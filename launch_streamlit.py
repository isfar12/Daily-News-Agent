"""
Startup script for the News Agent Streamlit App
"""

import subprocess
import sys
import os
from pathlib import Path

def check_environment():
    """Check if environment is properly set up"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("⚠️  No .env file found!")
        print("💡 Create a .env file with your API keys if needed:")
        print("   GROQ_API_KEY=your_groq_api_key_here")
        print("   # Add other API keys as needed")
    
    # Check if Ollama is running (optional)
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama is running and accessible")
        else:
            print("⚠️  Ollama might not be running properly")
    except Exception:
        print("⚠️  Ollama is not running or not accessible")
        print("💡 Make sure Ollama is installed and running:")
        print("   ollama serve")

def launch_streamlit():
    """Launch the Streamlit app"""
    print("🚀 Launching News Agent Streamlit App...")
    print("=" * 50)
    
    # Launch Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Shutting down the app...")
    except Exception as e:
        print(f"❌ Error launching Streamlit: {e}")

def main():
    """Main function"""
    print("🤖 News Agent Streamlit Launcher")
    print("=" * 40)
    
    # Check current directory
    current_dir = Path.cwd()
    print(f"📁 Current directory: {current_dir}")
    
    # Check if we're in the right directory
    if not Path("streamlit_app.py").exists():
        print("❌ streamlit_app.py not found in current directory!")
        print("💡 Make sure you're in the News Agent project directory")
        return
    
    print("✅ Found streamlit_app.py")
    
    
    # Check environment
    print("\n🔍 Checking environment...")
    check_environment()
    
    # Launch app
    print("\n" + "=" * 50)
    print("🎯 Ready to launch!")
    print("📱 The app will open in your default browser")
    print("🔗 URL: http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop the app")
    print("=" * 50)
    
    input("Press Enter to launch the Streamlit app...")
    launch_streamlit()

if __name__ == "__main__":
    main()