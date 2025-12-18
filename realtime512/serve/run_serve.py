"""Main entry point for realtime512 serve command."""

import os
from flask import Flask
from flask_cors import CORS

from .api_handlers import (
    get_config_handler,
    get_files_handler,
    get_shift_coefficients_handler,
    get_templates_handler,
    get_binary_data_handler,
    get_high_activity_handler,
    get_stats_handler,
    get_preview_file_handler,
)

def run_serve(host="0.0.0.0", port=5000):
    """Main entry point for realtime512 serve."""
    # Check if we're in an experiment directory
    config_path = os.path.join(os.getcwd(), "realtime512.yaml")
    if not os.path.exists(config_path):
        print("Error: No realtime512.yaml configuration file found in current directory.")
        print("Please run this command from an experiment directory.")
        return
    
    raw_dir = os.path.join(os.getcwd(), "raw")
    if not os.path.exists(raw_dir):
        print("Error: No raw/ directory found in current directory.")
        print("Please run this command from an experiment directory.")
        return
    
    print(f"Starting realtime512 server...")
    print(f"Serving data from: {os.getcwd()}")
    print(f"Server will listen on http://{host}:{port}")
    print(f"CORS enabled for: http://localhost:5173 and https://realtime512-dashboard.vercel.app")
    print("")
    print("API Endpoints:")
    print("  GET /api/config - Configuration")
    print("  GET /api/files - Available files and status")
    print("  GET /api/shift_coefficients - Shift coefficients")
    print("  GET /api/templates/<filename> - Templates (binary)")
    print("  GET /api/raw/<filename>?start_sec=X&end_sec=Y - Raw data")
    print("  GET /api/filt/<filename>?start_sec=X&end_sec=Y - Filtered data")
    print("  GET /api/shifted/<filename>?start_sec=X&end_sec=Y - Shifted data")
    print("  GET /api/high_activity/<filename> - High activity intervals")
    print("  GET /api/stats/<filename> - Spike statistics")
    print("  GET /api/preview/<filename>/<filepath> - Preview files (with range support)")
    print("")
    
    # Create Flask app
    app = Flask(__name__)

    # Enable CORS for localhost:5173 and https://realtime512-dashboard.vercel.app and expose custom headers
    CORS(app, origins=["http://localhost:5173", "https://realtime512-dashboard.vercel.app"], expose_headers=[
        "X-Start-Sec",
        "X-End-Sec", 
        "X-Num-Frames",
        "X-Num-Channels",
        "X-Sampling-Frequency"
    ])
    
    # Register routes
    @app.route("/api/config", methods=["GET"])
    def get_config():
        return get_config_handler()
    
    @app.route("/api/files", methods=["GET"])
    def get_files():
        return get_files_handler()
    
    @app.route("/api/shift_coefficients", methods=["GET"])
    def get_shift_coefficients():
        return get_shift_coefficients_handler()
    
    @app.route("/api/templates/<filename>", methods=["GET"])
    def get_templates(filename):
        return get_templates_handler(filename)
    
    @app.route("/api/raw/<filename>", methods=["GET"])
    def get_raw(filename):
        return get_binary_data_handler("raw", filename)
    
    @app.route("/api/filt/<filename>", methods=["GET"])
    def get_filt(filename):
        return get_binary_data_handler("filt", filename)
    
    @app.route("/api/shifted/<filename>", methods=["GET"])
    def get_shifted(filename):
        return get_binary_data_handler("shifted", filename)
    
    @app.route("/api/high_activity/<filename>", methods=["GET"])
    def get_high_activity(filename):
        return get_high_activity_handler(filename)
    
    @app.route("/api/stats/<filename>", methods=["GET"])
    def get_stats(filename):
        return get_stats_handler(filename)
    
    @app.route("/api/preview/<filename>/<path:filepath>", methods=["GET"])
    def get_preview_file(filename, filepath):
        return get_preview_file_handler(filename, filepath)
    
    # Run the server
    app.run(host=host, port=port, debug=False)
