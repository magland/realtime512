"""Handlers for focus units management."""

import os
import json
import hashlib
import numpy as np
import yaml
from flask import jsonify, request

def _get_focus_units_path():
    """Get path to focus_units.json file."""
    return os.path.join(os.getcwd(), "focus_units.json")

def _load_focus_units():
    """Load focus units from JSON file."""
    focus_units_path = _get_focus_units_path()
    
    if not os.path.exists(focus_units_path):
        return {"focus_units": []}
    
    try:
        with open(focus_units_path, "r") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        # If file is corrupted, return empty structure
        return {"focus_units": []}

def _save_focus_units(data):
    """Save focus units to JSON file."""
    focus_units_path = _get_focus_units_path()
    
    with open(focus_units_path, "w") as f:
        json.dump(data, f, indent=2)

def _calculate_spike_labels_hash(filename):
    """Calculate SHA-1 hash of spike_labels.npy file."""
    computed_dir = os.path.join(os.getcwd(), "computed")
    spike_labels_path = os.path.join(
        computed_dir, "coarse_sorting", filename, "spike_labels.npy"
    )
    
    if not os.path.exists(spike_labels_path):
        return None
    
    # Calculate SHA-1 hash of the file
    sha1 = hashlib.sha1()
    with open(spike_labels_path, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    
    return sha1.hexdigest()

def _get_next_focus_unit_id(existing_units):
    """Generate next focus unit ID based on existing units."""
    if not existing_units:
        return "F001"
    
    # Extract numeric parts from existing IDs
    max_num = 0
    for unit in existing_units:
        focus_id = unit.get("focus_unit_id", "")
        if focus_id.startswith("F"):
            try:
                num = int(focus_id[1:])
                max_num = max(max_num, num)
            except ValueError:
                continue
    
    # Generate next ID
    next_num = max_num + 1
    return f"F{next_num:03d}"

def get_focus_units_handler():
    """Get all focus units with mutual match information."""
    data = _load_focus_units()
    
    # Enrich each focus unit with mutual match data
    computed_dir = os.path.join(os.getcwd(), "computed")
    unit_matching_dir = os.path.join(computed_dir, "unit_matching")
    
    for focus_unit in data["focus_units"]:
        bin_filename = focus_unit["bin_filename"]
        unit_id = focus_unit["unit_id"]
        mutual_matches = []
        
        # Only proceed if unit_matching directory exists
        if not os.path.exists(unit_matching_dir):
            focus_unit["mutual_matches"] = mutual_matches
            continue
        
        # Scan all X directories in unit_matching
        for fname_x in os.listdir(unit_matching_dir):
            x_dir = os.path.join(unit_matching_dir, fname_x)
            if not os.path.isdir(x_dir):
                continue
            
            # Scan all Y directories under this X
            for fname_y in os.listdir(x_dir):
                y_dir = os.path.join(x_dir, fname_y)
                if not os.path.isdir(y_dir):
                    continue
                
                mutual_matches_path = os.path.join(y_dir, "mutual_matches.json")
                if not os.path.exists(mutual_matches_path):
                    continue
                
                try:
                    with open(mutual_matches_path, "r") as f:
                        matches = json.load(f)
                    
                    # Check if this focus unit appears in the matches
                    for match in matches:
                        unit_x = match.get("unit_x")
                        unit_y = match.get("unit_y")
                        overall_score = match.get("overall_score")
                        
                        # Check if our focus unit matches either side
                        if fname_x == bin_filename and unit_x == unit_id:
                            # Our focus unit is X, matched to Y
                            mutual_matches.append({
                                "bin_filename": fname_y,
                                "unit_id": unit_y,
                                "overall_score": overall_score
                            })
                        elif fname_y == bin_filename and unit_y == unit_id:
                            # Our focus unit is Y, matched to X
                            mutual_matches.append({
                                "bin_filename": fname_x,
                                "unit_id": unit_x,
                                "overall_score": overall_score
                            })
                
                except (json.JSONDecodeError, IOError):
                    # Skip files that can't be read
                    continue
        
        # Remove duplicates (same match might be found from both directions)
        seen = set()
        unique_matches = []
        for match in mutual_matches:
            key = (match["bin_filename"], match["unit_id"])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        focus_unit["mutual_matches"] = unique_matches
    
    return jsonify(data)

def add_focus_units_handler():
    """Add new focus units."""
    request_data = request.get_json()
    
    if not request_data or "units" not in request_data:
        return jsonify({"error": "Missing 'units' in request body"}), 400
    
    units_to_add = request_data["units"]
    
    if not isinstance(units_to_add, list) or len(units_to_add) == 0:
        return jsonify({"error": "'units' must be a non-empty array"}), 400
    
    # Load existing focus units
    data = _load_focus_units()
    existing_units = data["focus_units"]
    
    # Validate and add each unit
    added_units = []
    
    for unit_data in units_to_add:
        bin_filename = unit_data.get("bin_filename")
        unit_id = unit_data.get("unit_id")
        
        if not bin_filename or unit_id is None:
            return jsonify({
                "error": "Each unit must have 'bin_filename' and 'unit_id'"
            }), 400
        
        # Verify file has coarse sorting
        computed_dir = os.path.join(os.getcwd(), "computed")
        coarse_sorting_dir = os.path.join(computed_dir, "coarse_sorting", bin_filename)
        
        if not os.path.exists(os.path.join(coarse_sorting_dir, "spike_labels.npy")):
            return jsonify({
                "error": f"File {bin_filename} does not have coarse sorting"
            }), 400
        
        # Calculate hash
        spike_labels_hash = _calculate_spike_labels_hash(bin_filename)
        
        if spike_labels_hash is None:
            return jsonify({
                "error": f"Could not calculate hash for {bin_filename}"
            }), 500
        
        # Generate new focus unit ID
        focus_unit_id = _get_next_focus_unit_id(existing_units)
        
        # Create new focus unit
        new_unit = {
            "focus_unit_id": focus_unit_id,
            "bin_filename": bin_filename,
            "unit_id": int(unit_id),
            "notes": "",
            "spike_labels_hash": spike_labels_hash
        }
        
        existing_units.append(new_unit)
        added_units.append(new_unit)
    
    # Save updated data
    _save_focus_units(data)
    
    return jsonify({"added_units": added_units}), 201

def update_focus_unit_handler(focus_unit_id):
    """Update a focus unit (currently only notes)."""
    request_data = request.get_json()
    
    if not request_data or "notes" not in request_data:
        return jsonify({"error": "Missing 'notes' in request body"}), 400
    
    notes = request_data["notes"]
    
    # Load existing focus units
    data = _load_focus_units()
    
    # Find and update the unit
    unit_found = False
    for unit in data["focus_units"]:
        if unit["focus_unit_id"] == focus_unit_id:
            unit["notes"] = notes
            unit_found = True
            break
    
    if not unit_found:
        return jsonify({"error": f"Focus unit {focus_unit_id} not found"}), 404
    
    # Save updated data
    _save_focus_units(data)
    
    return jsonify({"success": True})

def delete_focus_unit_handler(focus_unit_id):
    """Delete a focus unit."""
    # Load existing focus units
    data = _load_focus_units()
    
    # Filter out the unit to delete
    original_count = len(data["focus_units"])
    data["focus_units"] = [
        unit for unit in data["focus_units"]
        if unit["focus_unit_id"] != focus_unit_id
    ]
    
    if len(data["focus_units"]) == original_count:
        return jsonify({"error": f"Focus unit {focus_unit_id} not found"}), 404
    
    # Save updated data
    _save_focus_units(data)
    
    return jsonify({"success": True})

def get_coarse_sorting_units_handler(filename):
    """Get available units from coarse sorting for a file."""
    computed_dir = os.path.join(os.getcwd(), "computed")
    coarse_sorting_dir = os.path.join(computed_dir, "coarse_sorting", filename)
    
    # Check if coarse sorting exists
    spike_labels_path = os.path.join(coarse_sorting_dir, "spike_labels.npy")
    
    if not os.path.exists(spike_labels_path):
        return jsonify({"error": "Coarse sorting not found for this file"}), 404
    
    # Load spike labels to get unique unit IDs
    try:
        spike_labels = np.load(spike_labels_path)
        unique_units = np.unique(spike_labels)
        
        # Count spikes per unit
        units_info = []
        for unit_id in unique_units:
            num_spikes = np.sum(spike_labels == unit_id)
            units_info.append({
                "unit_id": int(unit_id),
                "num_spikes": int(num_spikes)
            })
        
        # Sort by unit_id
        units_info.sort(key=lambda x: x["unit_id"])
        
        # Calculate current hash
        current_hash = _calculate_spike_labels_hash(filename)
        
        return jsonify({
            "units": units_info,
            "spike_labels_hash": current_hash
        })
    
    except Exception as e:
        return jsonify({"error": f"Error reading coarse sorting data: {str(e)}"}), 500

def get_spike_train_for_focus_unit_handler(focus_unit_id):
    """Get spike train data for a focus unit across all matched files."""
    # Load focus units
    data = _load_focus_units()
    
    # Find the requested focus unit
    focus_unit = None
    for unit in data["focus_units"]:
        if unit["focus_unit_id"] == focus_unit_id:
            focus_unit = unit
            break
    
    if focus_unit is None:
        return jsonify({"error": f"Focus unit {focus_unit_id} not found"}), 404
    
    # Load configuration to get sampling frequency and channels
    config_path = os.path.join(os.getcwd(), "realtime512.yaml")
    if not os.path.exists(config_path):
        return jsonify({"error": "Configuration file not found"}), 404
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    n_channels = config.get("n_channels", 512)
    sampling_frequency = config.get("sampling_frequency", 20000)
    
    # Get all .bin files sorted alphabetically (chronological order)
    raw_dir = os.path.join(os.getcwd(), "raw")
    computed_dir = os.path.join(os.getcwd(), "computed")
    
    if not os.path.exists(raw_dir):
        return jsonify({"error": "raw/ directory not found"}), 404
    
    bin_files = sorted([fname for fname in os.listdir(raw_dir) if fname.endswith(".bin")])
    
    # Build mutual matches lookup by scanning unit_matching directory
    mutual_matches_map = {}
    unit_matching_dir = os.path.join(computed_dir, "unit_matching")
    focus_bin_filename = focus_unit["bin_filename"]
    focus_unit_id_num = focus_unit["unit_id"]
    
    if os.path.exists(unit_matching_dir):
        # Check all X directories
        for fname_x in os.listdir(unit_matching_dir):
            x_dir = os.path.join(unit_matching_dir, fname_x)
            if not os.path.isdir(x_dir):
                continue
            
            # Check all Y directories under this X
            for fname_y in os.listdir(x_dir):
                y_dir = os.path.join(x_dir, fname_y)
                if not os.path.isdir(y_dir):
                    continue
                
                mutual_matches_path = os.path.join(y_dir, "mutual_matches.json")
                if not os.path.exists(mutual_matches_path):
                    continue
                
                try:
                    with open(mutual_matches_path, "r") as f:
                        matches = json.load(f)
                    
                    # Check if this focus unit appears in the matches
                    for match in matches:
                        unit_x = match.get("unit_x")
                        unit_y = match.get("unit_y")
                        
                        # Check if our focus unit matches either side
                        if fname_x == focus_bin_filename and unit_x == focus_unit_id_num:
                            # Our focus unit is X, matched to Y
                            mutual_matches_map[fname_y] = unit_y
                        elif fname_y == focus_bin_filename and unit_y == focus_unit_id_num:
                            # Our focus unit is Y, matched to X
                            mutual_matches_map[fname_x] = unit_x
                
                except (json.JSONDecodeError, IOError):
                    # Skip files that can't be read
                    continue
    
    # Build segments with spike times
    segments = []
    current_offset = 0.0
    total_spikes = 0
    
    for bin_filename in bin_files:
        # Calculate file duration
        raw_path = os.path.join(raw_dir, bin_filename)
        if not os.path.exists(raw_path):
            continue
        
        file_size = os.path.getsize(raw_path)
        num_frames = file_size // (2 * n_channels)
        duration_sec = num_frames / sampling_frequency
        
        segment_start = current_offset
        segment_end = current_offset + duration_sec
        
        # Check if this file has a matching unit
        is_focus_file = (bin_filename == focus_unit["bin_filename"])
        has_match = bin_filename in mutual_matches_map
        
        if is_focus_file or has_match:
            # Determine which unit to use
            if is_focus_file:
                unit_id = focus_unit["unit_id"]
            else:
                unit_id = mutual_matches_map[bin_filename]
            
            # Load spike times for this unit
            coarse_sorting_dir = os.path.join(computed_dir, "coarse_sorting", bin_filename)
            spike_times_path = os.path.join(coarse_sorting_dir, "spike_times.npy")
            spike_labels_path = os.path.join(coarse_sorting_dir, "spike_labels.npy")
            
            if os.path.exists(spike_times_path) and os.path.exists(spike_labels_path):
                spike_times = np.load(spike_times_path)
                spike_labels = np.load(spike_labels_path)
                
                # Filter spike times for this unit
                unit_mask = spike_labels == unit_id
                unit_spike_times = spike_times[unit_mask]
                
                # Apply offset to spike times
                offset_spike_times = unit_spike_times + current_offset
                
                num_spikes = len(unit_spike_times)
                total_spikes += num_spikes
                
                segments.append({
                    "bin_filename": bin_filename,
                    "unit_id": int(unit_id),
                    "start_time_offset": segment_start,
                    "end_time_offset": segment_end,
                    "num_spikes": num_spikes,
                    "spike_times": offset_spike_times.tolist(),
                    "is_focus_unit": is_focus_file,
                    "is_gap": False
                })
            else:
                # Coarse sorting not available for this file - treat as gap
                segments.append({
                    "bin_filename": bin_filename,
                    "unit_id": None,
                    "start_time_offset": segment_start,
                    "end_time_offset": segment_end,
                    "num_spikes": 0,
                    "spike_times": [],
                    "is_focus_unit": False,
                    "is_gap": True
                })
        else:
            # No match for this file - gap
            segments.append({
                "bin_filename": bin_filename,
                "unit_id": None,
                "start_time_offset": segment_start,
                "end_time_offset": segment_end,
                "num_spikes": 0,
                "spike_times": [],
                "is_focus_unit": False,
                "is_gap": True
            })
        
        current_offset = segment_end
    
    total_duration_sec = current_offset
    
    return jsonify({
        "focus_unit_id": focus_unit_id,
        "total_spikes": total_spikes,
        "total_duration_sec": total_duration_sec,
        "segments": segments
    })
