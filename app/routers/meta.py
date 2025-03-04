from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

router = APIRouter()

@router.get("/meta/webhook")
def verify_webhook(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None
):
    # Hardcode the token to "smartleadcrm123" for now
    if hub_mode == "subscribe" and hub_verify_token == "smartleadcrm123":
        # Return challenge as plain text
        return PlainTextResponse(hub_challenge)
    else:
        return PlainTextResponse("Verification failed", status_code=403)

@router.post("/meta/webhook")
async def receive_webhook(request: Request):
    """Simple webhook receiver that just acknowledges receipt"""
    try:
        # Just log that we received something
        return {"status": "success"}
    except Exception as e:
        # Always return 200 to Meta to prevent retries
        return {"status": "error", "message": "Error processing webhook"} 