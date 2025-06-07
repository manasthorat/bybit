import secrets
webhook_secret = secrets.token_urlsafe(32)
print(f"Add this to your .env file:")
print(f"WEBHOOK_SECRET={webhook_secret}")