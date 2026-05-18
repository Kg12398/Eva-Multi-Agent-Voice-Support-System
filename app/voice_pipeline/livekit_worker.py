"""
LiveKit Voice Pipeline Worker — The Real-Time Audio Engine.
Connects Twilio SIP → LiveKit Room → VAD → STT → Orchestrator → TTS → back to caller.
Handles barge-in (interruptions) and endpointing.
"""

import asyncio
import uuid
from typing import Dict
from livekit import agents, rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, silero

from app.voice_pipeline.sarvam_tts import SarvamTTS

from app.agents.orchestrator import Orchestrator
from app.services.redis_service import redis_service
from app.config import settings
from app.utils.constants import GREETING_MESSAGE, VAD_CONFIG, STT_CONFIG, TTS_CONFIG
from app.utils.logger import CallLogger, setup_logging
from app.utils.rag_loader import get_vector_store

# Pre-load knowledge base for RAG
vector_db = get_vector_store()
orchestrator = Orchestrator(vector_store=vector_db)

logger = CallLogger(call_id="livekit_worker")


# ============================================
# Minimal LLM Wrapper for Groq
# ============================================

class GroqLLM(llm.LLM):
    """
    A minimal LLM wrapper to satisfy LiveKit's internal requirements.
    Our actual logic is handled by the Orchestrator, so this just acts as a placeholder.
    """
    def __init__(self):
        super().__init__()

    def chat(self, *args, **kwargs):
        # This isn't used because we intercept speech committed
        return None

# ============================================
# LiveKit Agent Worker
# ============================================

# Track disconnect tasks per room to allow cancellation on barge-in
active_disconnect_tasks: Dict[str, asyncio.Task] = {}

async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for each incoming call.
    LiveKit creates a new Room for each SIP call from Twilio.
    This function is called once per call.
    """
    room_name = ctx.room.name or str(uuid.uuid4())
    call_id = room_name
    call_logger = CallLogger(call_id=call_id)
    call_logger.info("New call received, connecting services...")

    # Connect to databases
    from app.services.db_service import db_service
    await redis_service.connect()
    await db_service.connect()

    # QUICK! Connect to the room immediately to satisfy LiveKit's 10-second timeout rule
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    call_logger.info("Room connected, initializing agent...")
    
    # Wait for a participant (the caller via SIP)
    participant = await ctx.wait_for_participant()
    call_logger.info(f"Participant connected: {participant.identity}")

    # Extract phone number from participant metadata if available
    phone_number = participant.identity or ""

    # Start the call session
    greeting = await orchestrator.start_call(call_id, phone_number)

    # official callback to handle the "Brain" logic
    async def before_llm_cb(agent: VoicePipelineAgent, chat_ctx: llm.ChatContext):
        """
        This is called by LiveKit as soon as the user finishes speaking.
        We take the transcript, run it through our Orchestrator,
        and then manually trigger the speech.
        """
        # 1. CANCEL PENDING DISCONNECT if user speaks again
        if call_id in active_disconnect_tasks:
            call_logger.info("User interrupted during closure — canceling disconnect timer.")
            task = active_disconnect_tasks.pop(call_id)
            task.cancel()

        user_msg = chat_ctx.messages[-1]
        user_text = user_msg.content if hasattr(user_msg, 'content') else str(user_msg)
        
        call_logger.info(f"User said: {user_text[:100]}")
        
        try:
            # 2. Run our Brain
            response_text = await orchestrator.process_turn(call_id, user_text)
            
            if response_text:
                call_logger.info(f"Gauri response: {response_text[:100]}")
                # Manually speak the response
                await agent.say(response_text)

            # 3. DYNAMIC DISCONNECT logic
            from app.services.redis_service import redis_service as rs
            from app.models.call_state import CallState
            session = await rs.get_session(call_id)
            if session and session.state == CallState.END:
                # Calculate duration: ~1s per 10 chars + buffer
                wait_time = max(8, (len(response_text) / 10) + 5)
                call_logger.info(f"Call tagged for END — starting {wait_time:.1f}s disconnect timer.")
                
                async def deferred_disconnect(delay: float, cid: str):
                    try:
                        await asyncio.sleep(delay)
                        if cid in active_disconnect_tasks:
                            call_logger.info("Disconnect timer expired — closing room.")
                            await ctx.room.disconnect()
                            active_disconnect_tasks.pop(cid, None)
                    except asyncio.CancelledError:
                        call_logger.info(f"Disconnect task for {cid} was cancelled safely.")

                active_disconnect_tasks[call_id] = asyncio.create_task(deferred_disconnect(wait_time, call_id))
            
            # CRITICAL: Return False to tell LiveKit NOT to run its own internal synthesis
            return False
            
        except Exception as e:
            call_logger.error(f"Orchestrator error: {e}", exc_info=True)
            await agent.say("I'm sorry, I'm having a bit of trouble. Could you repeat that?")
            return False

    # ---- Build the Voice Pipeline ----
    agent = VoicePipelineAgent(
        vad=silero.VAD.load(
            min_silence_duration=VAD_CONFIG["min_silence_duration_ms"] / 1000,
        ),
        stt=deepgram.STT(
            api_key=settings.DEEPGRAM_API_KEY,
            model=STT_CONFIG["model"],
            interim_results=True,
            smart_format=True,
        ),
        llm=GroqLLM(), 
        tts=SarvamTTS(
            api_key=settings.SARVAM_API_KEY,
            speaker=settings.SARVAM_TTS_SPEAKER,
            model=settings.SARVAM_TTS_MODEL,
            language=settings.SARVAM_TTS_LANGUAGE,
            pace=TTS_CONFIG["pace"],
            sample_rate=TTS_CONFIG["sample_rate"],
        ),
        # PLUG IN OUR BRAIN HERE
        before_llm_cb=before_llm_cb,
        
        allow_interruptions=True,
        interrupt_speech_duration=0.5,
        interrupt_min_words=2,
    )

    # Start the agent
    agent.start(ctx.room, participant)

    # Speak the greeting
    print(f"DEBUG: Attempting to speak greeting: '{greeting}'")
    await agent.say(greeting)
    print("DEBUG: Greeting command sent.")

    call_logger.info("Agent started and listening...")

    # Keep alive until room is disconnected
    try:
        while ctx.room.connection_state == rtc.ConnectionState.CONNECTED:
            await asyncio.sleep(1)
    finally:
        await agent.aclose()
    session = await orchestrator.end_call(call_id)

    # TODO: Queue background jobs:
    # - Save call record to PostgreSQL
    # - Generate call summary
    # - Upload audio recording to S3


# ============================================
# Process Initialization
# ============================================

def prewarm(proc: JobProcess):
    """
    Called once when the worker process starts.
    Use this to preload models (like Silero VAD) to avoid cold-start latency.
    """
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Worker prewarmed: VAD model loaded")


# ============================================
# Main Entry Point
# ============================================

def start_worker():
    """Start the LiveKit agent worker."""
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info("Starting KG ElectroPower Voice Agent Worker...")

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
            ws_url=settings.LIVEKIT_URL,
        ),
    )


if __name__ == "__main__":
    start_worker()
