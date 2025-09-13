from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="crisiscast.env")

print("✅ OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY")[:10] + "...")
print("✅ POLYGON_API_KEY:", os.getenv("POLYGON_API_KEY")[:10] + "...")
print("✅ GNEWS_API_KEY:", os.getenv("GNEWS_API_KEY"))
print("✅ HUGGINGFACE_API_KEY:", os.getenv("HUGGINGFACE_API_KEY")[:10] + "...")

