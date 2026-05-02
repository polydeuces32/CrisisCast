from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="crisiscast.env")

print("[OK] OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY")[:10] + "...")
print("[OK] POLYGON_API_KEY:", os.getenv("POLYGON_API_KEY")[:10] + "...")
print("[OK] GNEWS_API_KEY:", os.getenv("GNEWS_API_KEY"))
print("[OK] HUGGINGFACE_API_KEY:", os.getenv("HUGGINGFACE_API_KEY")[:10] + "...")

