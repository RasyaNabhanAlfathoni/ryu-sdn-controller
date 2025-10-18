#!/usr/bin/env python3
"""
Web Dashboard for Ryu SDN Controller
"""
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import requests
import json
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configuration
RYU_CONTROLLER_URL = os.environ.get("RYU_CONTROLLER_URL", "http://192.168.221.133:8080")
RYU_API_KEY = os.environ.get("RYU_API_KEY", "agent-secret-token-1")

headers = {
    "Content-Type": "application/json",
    "X-API-KEY": RYU_API_KEY
}

def get_devices():
    """Get all devices from Ryu controller"""
    try:
        response = requests.get(f"{RYU_CONTROLLER_URL}/devices", headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        print(f"Error getting devices: {e}")
        return []

def create_job(device_id, action, params=None):
    """Create a job in Ryu controller"""
    payload = {
        "device_id": device_id,
        "action": action,
        "params": params or {}
    }
    
    try:
        response = requests.post(f"{RYU_CONTROLLER_URL}/jobs", 
                               headers=headers, 
                               json=payload, 
                               timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_job_status(job_id):
    """Get job status from Ryu controller"""
    try:
        response = requests.get(f"{RYU_CONTROLLER_URL}/jobs/{job_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Job not found"}
    except Exception as e:
        return {"error": str(e)}

# Routes
@app.route('/')
def index():
    """Dashboard homepage"""
    devices = get_devices()
    
    # Count devices by role
    manager_count = len([d for d in devices if d.get('role') == 'manager'])
    agent_count = len([d for d in devices if d.get('role') == 'agent'])
    
    return render_template('index.html', 
                         devices=devices,
                         manager_count=manager_count,
                         agent_count=agent_count,
                         total_devices=len(devices))

@app.route('/devices')
def devices():
    """Devices management page"""
    devices_list = get_devices()
    return render_template('devices.html', devices=devices_list)

@app.route('/jobs')
def jobs():
    """Jobs monitoring page"""
    return render_template('jobs.html')

@app.route('/api/devices')
def api_devices():
    """API endpoint for devices (for AJAX)"""
    return jsonify(get_devices())

@app.route('/api/jobs', methods=['POST'])
def api_create_job():
    """API endpoint to create jobs"""
    data = request.json
    device_id = data.get('device_id')
    action = data.get('action')
    params = data.get('params', {})

    print(f"DEBUG: Creating job - device_id: {device_id}, action: {action}")
    
    result = create_job(device_id, action, params)
    return jsonify(result)

@app.route('/api/jobs/<job_id>')
def api_get_job(job_id):
    """API endpoint to get job status"""
    result = get_job_status(job_id)
    return jsonify(result)

@app.route('/monitor/<device_id>')
def monitor_device(device_id):
    """Monitor specific device"""
    job_result = create_job(device_id, "server.monitor")
    
    if 'job_id' in job_result:
        flash(f"Monitoring job created: {job_result['job_id']}", "success")
    else:
        flash(f"Error creating monitoring job: {job_result.get('error', 'Unknown error')}", "error")
    
    return redirect(url_for('devices'))

@app.route('/server_info/<device_id>')
def server_info(device_id):
    """Get server information"""
    job_result = create_job(device_id, "server.ip.show_all")
    
    if 'job_id' in job_result:
        flash(f"Server info job created: {job_result['job_id']}", "success")
    else:
        flash(f"Error: {job_result.get('error', 'Unknown error')}", "error")
    
    return redirect(url_for('devices'))

@app.route('/network')
def network_management():
    """Network management page"""
    return render_template('network.html')

@app.route('/firewall')
def firewall_management():
    """Firewall management page"""
    return render_template('firewall.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)