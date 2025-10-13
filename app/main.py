from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.health import router as health_router
from app.api.inference import router as inference_router
from app.core import configure_logging, http_exception_handler, general_exception_handler
from app.clients.kafka_client import KafkaClient
from app.consumers.event_consumer import create_event_consumer
from app.clients.progress_service import ProgressServiceClient

settings = get_settings()

# Configure logging with enhanced formatting
# Use colorized console logging for development, JSON for production
logger = configure_logging(
    service_name="ai-service",
    log_level="INFO" if settings.is_production else "DEBUG",
    format_type="json" if settings.is_production else "console"
)

# progress = ProgressServiceClient()
# print(progress.get_student_interaction_history("devinda"))

app = FastAPI(
    title=settings.APP_NAME, 
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION
)

# Store logger in app state for access in exception handlers
app.state.logger = logger

# Initialize Kafka client and event consumer (will be started in startup event)
kafka_client: KafkaClient = None
event_consumer = None

# Add exception handlers for structured logging
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(inference_router, prefix="/inference", tags=["inference"])

@app.on_event("startup")
async def startup_event():
    """Initialize services and start Kafka consumer on application startup."""
    global kafka_client, event_consumer
    
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in {settings.ENV} environment"
    )
    
    try:
        # Initialize Kafka client
        kafka_client = KafkaClient(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=settings.KAFKA_CLIENT_ID,
            logger=logger
        )
        
        # Start Kafka client
        await kafka_client.start()
        logger.info("Kafka client started successfully")
        
        # Initialize event consumer
        event_consumer = create_event_consumer(logger=logger)
        
        # Subscribe to events topic
        await kafka_client.subscribe(
            topics=[settings.KAFKA_EVENTS_TOPIC],
            group_id=settings.KAFKA_CONSUMER_GROUP_ID,
            handler=event_consumer.handle_event,
            auto_start=True
        )
        
        logger.info(
            f"Successfully subscribed to Kafka topic",
            extra={
                "topic": settings.KAFKA_EVENTS_TOPIC,
                "group_id": settings.KAFKA_CONSUMER_GROUP_ID
            }
        )
        
    except Exception as e:
        logger.error(
            f"Failed to initialize Kafka consumer: {str(e)}",
            extra={"error": str(e)}
        )
        # Don't fail startup if Kafka is unavailable
        # The service can still handle HTTP requests

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown."""
    global kafka_client
    
    logger.info(f"Shutting down {settings.APP_NAME}")
    
    # Stop Kafka client and all consumers
    if kafka_client:
        try:
            await kafka_client.stop()
            logger.info("Kafka client stopped successfully")
        except Exception as e:
            logger.error(
                f"Error stopping Kafka client: {str(e)}",
                extra={"error": str(e)}
            )

@app.get("/")
def read_root():
    """Root endpoint with welcome message."""
    logger.info("Root endpoint accessed")
    return {"message": f"Welcome to {settings.APP_NAME}!", "version": settings.APP_VERSION}