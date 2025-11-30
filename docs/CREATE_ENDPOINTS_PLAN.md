# Create Tab Backend Endpoints Implementation Plan

## Overview
This document outlines the implementation plan for the Create tab backend API endpoints. These endpoints support the ComfyUI workflow system, enabling users to discover workflows, generate customized workflow JSON files, and execute them on remote instances.

---

## 1. Architecture Overview

### 1.1 Endpoint Structure
```
/create/workflows/list         GET     - List available workflows
/create/workflows/<id>         GET     - Get workflow details and YAML config
/create/generate-workflow      POST    - Generate workflow JSON from inputs
/create/execute                POST    - Queue workflow execution on instance
/create/status/<task_id>       GET     - Get execution status
/create/cancel/<task_id>       POST    - Cancel running workflow
```

### 1.2 Data Flow
```
User fills form → Frontend collects inputs → Backend generates JSON
    ↓
Backend merges inputs with workflow template
    ↓
Backend validates required fields and models
    ↓
Backend returns generated workflow JSON or queues execution
    ↓
(For execution) Backend submits to ComfyUI via SSH/API
    ↓
Backend polls for status and returns results
```

### 1.3 File Structure
```
app/
├── api/
│   └── create.py                    (Flask blueprint for Create endpoints)
├── create/
│   ├── __init__.py
│   ├── workflow_loader.py           (Load and parse .webui.yml files)
│   ├── workflow_generator.py        (Generate workflow JSON from inputs)
│   ├── workflow_validator.py        (Validate inputs and requirements)
│   ├── workflow_executor.py         (Execute workflows on instances)
│   └── task_manager.py              (Manage async execution tasks)
└── workflows/
    ├── *.json                        (ComfyUI workflow templates)
    └── *.webui.yml                   (WebUI wrapper definitions)
```

---

## 2. Endpoint Specifications

### 2.1 List Available Workflows

**Endpoint**: `GET /create/workflows/list`

**Purpose**: Return list of all available workflows with metadata

**Request**: None (GET request)

**Response**:
```json
{
  "success": true,
  "workflows": [
    {
      "id": "IMG_to_VIDEO",
      "name": "IMG to VIDEO",
      "description": "Generate video from image using WAN 2.2",
      "category": "video",
      "version": "2.0.0",
      "thumbnail": "/static/workflows/thumbnails/img_to_video.png",
      "tags": ["image-to-video", "wan-2.2", "video-generation"],
      "vram_estimate": "24GB",
      "time_estimate": {
        "min": 120,
        "max": 600,
        "note": "Varies by duration and resolution"
      }
    }
  ]
}
```

**Implementation**:
```python
@bp.route('/workflows/list', methods=['GET'])
def list_workflows():
    """List all available workflows from workflows directory"""
    workflows = WorkflowLoader.discover_workflows()
    return jsonify({
        'success': True,
        'workflows': [w.to_dict() for w in workflows]
    })
```

**Logic**:
1. Scan `workflows/` directory for `*.webui.yml` files
2. Parse YAML metadata (name, description, category, etc.)
3. Check if corresponding `*.json` workflow file exists
4. Return array of workflow metadata
5. Cache results for 5 minutes

---

### 2.2 Get Workflow Details

**Endpoint**: `GET /create/workflows/<workflow_id>`

**Purpose**: Return full workflow configuration including all inputs, sections, and layout

**Request**: 
- Path parameter: `workflow_id` (e.g., "IMG_to_VIDEO")

**Response**:
```json
{
  "success": true,
  "workflow": {
    "id": "IMG_to_VIDEO",
    "name": "IMG to VIDEO",
    "description": "Generate video from image using WAN 2.2",
    "version": "2.0.0",
    "category": "video",
    "workflow_file": "IMG to VIDEO.json",
    "vram_estimate": "24GB",
    "layout": {
      "sections": [
        {
          "id": "basic",
          "title": "Basic Settings",
          "collapsed": false
        }
      ]
    },
    "inputs": [
      {
        "id": "input_image",
        "section": "basic",
        "node_id": "88",
        "field": "image",
        "type": "image",
        "label": "Input Image",
        "description": "Source image to animate",
        "required": true,
        "accept": "image/png,image/jpeg,image/webp",
        "max_size_mb": 10
      }
    ],
    "outputs": [
      {
        "id": "original_video",
        "node_id": "398",
        "type": "video",
        "format": "mp4",
        "label": "Original Video"
      }
    ]
  }
}
```

**Implementation**:
```python
@bp.route('/workflows/<workflow_id>', methods=['GET'])
def get_workflow_details(workflow_id):
    """Get full workflow configuration"""
    try:
        workflow = WorkflowLoader.load_workflow(workflow_id)
        return jsonify({
            'success': True,
            'workflow': workflow.to_dict()
        })
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'message': f'Workflow not found: {workflow_id}'
        }), 404
```

**Logic**:
1. Load `{workflow_id}.webui.yml` from workflows directory
2. Parse YAML with full configuration
3. Validate structure (required fields present)
4. Return complete workflow object
5. Cache parsed YAML for 5 minutes

---

### 2.3 Generate Workflow JSON

**Endpoint**: `POST /create/generate-workflow`

**Purpose**: Generate a ComfyUI-compatible workflow JSON file with user inputs merged

**Request**:
```json
{
  "workflow_id": "IMG_to_VIDEO",
  "inputs": {
    "positive_prompt": "The young woman turns towards the camera",
    "negative_prompt": "blurry, low quality...",
    "input_image": "00262-3870373875.png",
    "duration": 5.0,
    "steps": 20,
    "cfg": 3.5,
    "frame_rate": 16.0,
    "seed": 495100899429947,
    "custom_size": false,
    "size_x": 896,
    "size_y": 1120,
    "main_model": {
      "highNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
      "lowNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors"
    },
    "loras": [
      {
        "highNoisePath": "loras/motion_enhance_high_noise.safetensors",
        "lowNoisePath": "loras/motion_enhance_low_noise.safetensors",
        "strength": 0.8
      }
    ],
    "clip_model": {
      "path": "Wan-2.2/umt5_xxl_fp16.safetensors"
    },
    "vae_model": {
      "path": "Wan-2.1/wan_2.1_vae.safetensors"
    },
    "upscale_model": {
      "path": "RealESRGAN_x4plus.pth"
    },
    "enable_interpolation": false,
    "enable_upscale_interpolation": true,
    "enable_video_enhancer": true,
    "enable_cfgzerostar": true,
    "enable_blockswap": true,
    "vram_reduction": 100
  }
}
```

**Response**:
```json
{
  "success": true,
  "workflow": {
    "73": {
      "inputs": {
        "noise_seed": 495100899429947
      },
      "class_type": "RandomNoise",
      "_meta": {
        "title": "Noise"
      }
    },
    "88": {
      "inputs": {
        "image": "00262-3870373875.png"
      },
      "class_type": "LoadImage",
      "_meta": {
        "title": "Load Image"
      }
    }
  },
  "metadata": {
    "workflow_id": "IMG_to_VIDEO",
    "version": "2.0.0",
    "generated_at": "2025-11-29T12:34:56Z",
    "input_summary": {
      "positive_prompt": "The young woman turns...",
      "duration": 5.0,
      "steps": 20
    }
  }
}
```

**Implementation**:
```python
@bp.route('/generate-workflow', methods=['POST'])
def generate_workflow():
    """Generate workflow JSON from inputs"""
    data = request.get_json()
    
    workflow_id = data.get('workflow_id')
    inputs = data.get('inputs', {})
    
    if not workflow_id:
        return jsonify({
            'success': False,
            'message': 'workflow_id is required'
        }), 400
    
    try:
        # Load workflow template and config
        workflow_config = WorkflowLoader.load_workflow(workflow_id)
        workflow_template = WorkflowLoader.load_workflow_json(workflow_id)
        
        # Validate inputs
        validator = WorkflowValidator(workflow_config)
        validation_result = validator.validate_inputs(inputs)
        
        if not validation_result.is_valid:
            return jsonify({
                'success': False,
                'message': 'Input validation failed',
                'errors': validation_result.errors
            }), 400
        
        # Generate workflow JSON
        generator = WorkflowGenerator(workflow_config, workflow_template)
        generated_workflow = generator.generate(inputs)
        
        # Add metadata
        metadata = {
            'workflow_id': workflow_id,
            'version': workflow_config.version,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'input_summary': generator.get_input_summary(inputs)
        }
        
        return jsonify({
            'success': True,
            'workflow': generated_workflow,
            'metadata': metadata
        })
        
    except Exception as e:
        logger.error(f"Error generating workflow: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

**Logic**:
1. Load workflow YAML config
2. Load workflow JSON template
3. Validate all required inputs are present
4. Validate input types and ranges
5. Map inputs to workflow nodes using config mappings
6. Handle special component types (high-low pairs, LoRAs, etc.)
7. Apply conditional logic (depends_on fields)
8. Return generated workflow JSON

---

### 2.4 Execute Workflow

**Endpoint**: `POST /create/execute`

**Purpose**: Queue workflow execution on a remote ComfyUI instance

**Request**:
```json
{
  "ssh_connection": "ssh -p 2838 root@104.189.178.116",
  "workflow_id": "IMG_to_VIDEO",
  "inputs": {
    "positive_prompt": "The young woman turns towards the camera",
    "input_image": "00262-3870373875.png"
  },
  "options": {
    "output_directory": "/workspace/outputs",
    "save_workflow": true,
    "notify_on_complete": false
  }
}
```

**Response**:
```json
{
  "success": true,
  "task_id": "task_abc123def456",
  "message": "Workflow queued successfully",
  "estimated_time": 300,
  "status_url": "/create/status/task_abc123def456"
}
```

**Implementation**:
```python
@bp.route('/execute', methods=['POST'])
def execute_workflow():
    """Execute workflow on remote instance"""
    data = request.get_json()
    
    ssh_connection = data.get('ssh_connection')
    workflow_id = data.get('workflow_id')
    inputs = data.get('inputs', {})
    options = data.get('options', {})
    
    if not ssh_connection or not workflow_id:
        return jsonify({
            'success': False,
            'message': 'ssh_connection and workflow_id are required'
        }), 400
    
    try:
        # Generate workflow JSON
        workflow_config = WorkflowLoader.load_workflow(workflow_id)
        workflow_template = WorkflowLoader.load_workflow_json(workflow_id)
        
        # Validate inputs
        validator = WorkflowValidator(workflow_config)
        validation_result = validator.validate_inputs(inputs)
        
        if not validation_result.is_valid:
            return jsonify({
                'success': False,
                'message': 'Input validation failed',
                'errors': validation_result.errors
            }), 400
        
        # Generate workflow
        generator = WorkflowGenerator(workflow_config, workflow_template)
        generated_workflow = generator.generate(inputs)
        
        # Create execution task
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        executor = WorkflowExecutor(ssh_connection)
        
        # Queue execution (async)
        task = executor.queue_execution(
            task_id=task_id,
            workflow_id=workflow_id,
            workflow_json=generated_workflow,
            options=options
        )
        
        # Store task in manager
        TaskManager.register_task(task_id, task)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Workflow queued successfully',
            'estimated_time': workflow_config.time_estimate.get('max', 300),
            'status_url': f'/create/status/{task_id}'
        })
        
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

**Logic**:
1. Validate SSH connection and workflow ID
2. Generate workflow JSON from inputs
3. Create unique task ID
4. Upload workflow JSON to instance
5. Submit to ComfyUI queue via API
6. Start background polling thread
7. Return task ID immediately
8. Store task metadata in Redis/memory

---

### 2.5 Get Execution Status

**Endpoint**: `GET /create/status/<task_id>`

**Purpose**: Get current status of executing workflow

**Request**: 
- Path parameter: `task_id`

**Response**:
```json
{
  "success": true,
  "task_id": "task_abc123def456",
  "status": "running",
  "progress": {
    "current_step": 15,
    "total_steps": 20,
    "percent": 75,
    "message": "Generating frame 15/20"
  },
  "started_at": "2025-11-29T12:34:56Z",
  "elapsed_seconds": 180,
  "estimated_remaining_seconds": 60,
  "outputs": [],
  "metadata": {
    "workflow_id": "IMG_to_VIDEO",
    "instance": "104.189.178.116:2838"
  }
}
```

**Status Values**:
- `queued` - Waiting to start
- `uploading` - Uploading workflow/assets
- `running` - Currently executing
- `complete` - Successfully finished
- `failed` - Execution failed
- `cancelled` - Cancelled by user

**Implementation**:
```python
@bp.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get execution status for a task"""
    task = TaskManager.get_task(task_id)
    
    if not task:
        return jsonify({
            'success': False,
            'message': f'Task not found: {task_id}'
        }), 404
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': task.status,
        'progress': task.get_progress(),
        'started_at': task.started_at.isoformat() + 'Z' if task.started_at else None,
        'elapsed_seconds': task.get_elapsed_seconds(),
        'estimated_remaining_seconds': task.get_estimated_remaining(),
        'outputs': task.get_outputs(),
        'metadata': task.metadata,
        'error': task.error if task.status == 'failed' else None
    })
```

**Logic**:
1. Look up task by ID in TaskManager
2. Return current status and progress
3. Include any error messages if failed
4. List output files if complete

---

### 2.6 Cancel Workflow

**Endpoint**: `POST /create/cancel/<task_id>`

**Purpose**: Cancel a running workflow execution

**Request**: None (POST to path)

**Response**:
```json
{
  "success": true,
  "task_id": "task_abc123def456",
  "message": "Workflow cancelled successfully"
}
```

**Implementation**:
```python
@bp.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """Cancel a running task"""
    task = TaskManager.get_task(task_id)
    
    if not task:
        return jsonify({
            'success': False,
            'message': f'Task not found: {task_id}'
        }), 404
    
    if task.status in ['complete', 'failed', 'cancelled']:
        return jsonify({
            'success': False,
            'message': f'Cannot cancel task with status: {task.status}'
        }), 400
    
    try:
        task.cancel()
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Workflow cancelled successfully'
        })
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

---

## 3. Core Components Implementation

### 3.1 WorkflowLoader

**File**: `app/create/workflow_loader.py`

**Purpose**: Load and parse workflow YAML and JSON files

**Key Methods**:
```python
class WorkflowLoader:
    @staticmethod
    def discover_workflows() -> List[WorkflowMetadata]:
        """Scan workflows directory and return metadata"""
        
    @staticmethod
    def load_workflow(workflow_id: str) -> WorkflowConfig:
        """Load and parse .webui.yml file"""
        
    @staticmethod
    def load_workflow_json(workflow_id: str) -> dict:
        """Load workflow JSON template"""
        
    @staticmethod
    def _parse_yaml_config(yaml_path: str) -> WorkflowConfig:
        """Parse YAML into WorkflowConfig object"""
```

**Implementation Details**:
- Cache parsed YAML for 5 minutes
- Validate YAML structure on load
- Handle missing files gracefully
- Support versioning

---

### 3.2 WorkflowGenerator

**File**: `app/create/workflow_generator.py`

**Purpose**: Generate ComfyUI workflow JSON from inputs

**Key Methods**:
```python
class WorkflowGenerator:
    def __init__(self, config: WorkflowConfig, template: dict):
        self.config = config
        self.template = template
        
    def generate(self, inputs: dict) -> dict:
        """Generate workflow JSON from inputs"""
        workflow = copy.deepcopy(self.template)
        
        for input_config in self.config.inputs:
            self._apply_input(workflow, input_config, inputs)
            
        return workflow
        
    def _apply_input(self, workflow: dict, input_config: InputConfig, inputs: dict):
        """Apply single input to workflow"""
        input_type = input_config.type
        
        if input_type == 'text' or input_type == 'textarea':
            self._apply_text_input(workflow, input_config, inputs)
        elif input_type == 'slider':
            self._apply_slider_input(workflow, input_config, inputs)
        elif input_type == 'high_low_pair_model':
            self._apply_high_low_model(workflow, input_config, inputs)
        elif input_type == 'high_low_pair_lora_list':
            self._apply_lora_list(workflow, input_config, inputs)
        # ... handle all input types
        
    def _apply_high_low_model(self, workflow: dict, config: InputConfig, inputs: dict):
        """Apply high-low noise model pair"""
        value = inputs.get(config.id)
        if not value:
            return
            
        high_node_id = config.node_ids[0]
        low_node_id = config.node_ids[1]
        
        workflow[high_node_id]['inputs']['unet_name'] = value['highNoisePath']
        workflow[low_node_id]['inputs']['unet_name'] = value['lowNoisePath']
        
    def _apply_lora_list(self, workflow: dict, config: InputConfig, inputs: dict):
        """Apply LoRA list to Power Lora Loader nodes"""
        loras = inputs.get(config.id, [])
        if not loras:
            return
            
        high_node_id = config.node_ids[0]
        low_node_id = config.node_ids[1]
        
        # Build Power Lora Loader config
        high_lora_config = {}
        low_lora_config = {}
        
        for idx, lora in enumerate(loras):
            key = f"Lora {idx + 1}"
            high_lora_config[key] = {
                'on': True,
                'lora': lora['highNoisePath'],
                'strength': lora['strength'],
                'strength_clip': lora['strength']
            }
            low_lora_config[key] = {
                'on': True,
                'lora': lora['lowNoisePath'],
                'strength': lora['strength'],
                'strength_clip': lora['strength']
            }
        
        workflow[high_node_id]['inputs']['➕ Add Lora'] = high_lora_config
        workflow[low_node_id]['inputs']['➕ Add Lora'] = low_lora_config
```

---

### 3.3 WorkflowValidator

**File**: `app/create/workflow_validator.py`

**Purpose**: Validate user inputs against workflow requirements

**Key Methods**:
```python
class ValidationResult:
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        
    def add_error(self, field: str, message: str):
        self.is_valid = False
        self.errors.append({'field': field, 'message': message})

class WorkflowValidator:
    def __init__(self, config: WorkflowConfig):
        self.config = config
        
    def validate_inputs(self, inputs: dict) -> ValidationResult:
        """Validate all inputs"""
        result = ValidationResult()
        
        for input_config in self.config.inputs:
            self._validate_input(input_config, inputs, result)
            
        return result
        
    def _validate_input(self, config: InputConfig, inputs: dict, result: ValidationResult):
        """Validate single input"""
        value = inputs.get(config.id)
        
        # Check required
        if config.required and not value:
            result.add_error(config.id, f'{config.label} is required')
            return
            
        # Type-specific validation
        if config.type == 'slider':
            self._validate_slider(config, value, result)
        elif config.type == 'image':
            self._validate_image(config, value, result)
        # ... handle all types
        
    def _validate_slider(self, config: InputConfig, value, result: ValidationResult):
        """Validate slider value in range"""
        if value < config.min or value > config.max:
            result.add_error(
                config.id,
                f'{config.label} must be between {config.min} and {config.max}'
            )
```

---

### 3.4 WorkflowExecutor

**File**: `app/create/workflow_executor.py`

**Purpose**: Execute workflows on remote ComfyUI instances

**Key Methods**:
```python
class WorkflowExecutor:
    def __init__(self, ssh_connection: str):
        self.ssh_connection = ssh_connection
        self.ssh_host, self.ssh_port = self._parse_connection(ssh_connection)
        
    def queue_execution(self, task_id: str, workflow_id: str, 
                       workflow_json: dict, options: dict) -> ExecutionTask:
        """Queue workflow for execution"""
        task = ExecutionTask(
            task_id=task_id,
            workflow_id=workflow_id,
            ssh_connection=self.ssh_connection,
            options=options
        )
        
        # Start async execution
        thread = threading.Thread(
            target=self._execute_workflow_async,
            args=(task, workflow_json)
        )
        thread.daemon = True
        thread.start()
        
        return task
        
    def _execute_workflow_async(self, task: ExecutionTask, workflow_json: dict):
        """Async execution in background thread"""
        try:
            task.status = 'uploading'
            
            # Upload workflow JSON to instance
            workflow_path = self._upload_workflow(workflow_json)
            
            task.status = 'running'
            
            # Submit to ComfyUI API
            prompt_id = self._submit_to_comfyui(workflow_json)
            task.comfyui_prompt_id = prompt_id
            
            # Poll for completion
            self._poll_until_complete(task, prompt_id)
            
            task.status = 'complete'
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            task.status = 'failed'
            task.error = str(e)
            
    def _upload_workflow(self, workflow_json: dict) -> str:
        """Upload workflow JSON to instance via SCP"""
        temp_file = f"/tmp/workflow_{uuid.uuid4().hex}.json"
        
        with open(temp_file, 'w') as f:
            json.dump(workflow_json, f, indent=2)
        
        remote_path = f"/workspace/workflows/generated_{uuid.uuid4().hex}.json"
        
        scp_cmd = [
            'scp',
            '-P', str(self.ssh_port),
            '-i', '/root/.ssh/id_ed25519',
            temp_file,
            f'root@{self.ssh_host}:{remote_path}'
        ]
        
        subprocess.run(scp_cmd, check=True)
        os.remove(temp_file)
        
        return remote_path
        
    def _submit_to_comfyui(self, workflow_json: dict) -> str:
        """Submit workflow to ComfyUI API"""
        # ComfyUI API endpoint
        api_url = f"http://{self.ssh_host}:8188/prompt"
        
        payload = {
            "prompt": workflow_json,
            "client_id": f"vastai_{uuid.uuid4().hex[:8]}"
        }
        
        response = requests.post(api_url, json=payload)
        data = response.json()
        
        return data['prompt_id']
        
    def _poll_until_complete(self, task: ExecutionTask, prompt_id: str):
        """Poll ComfyUI for completion status"""
        history_url = f"http://{self.ssh_host}:8188/history/{prompt_id}"
        
        while task.status == 'running':
            try:
                response = requests.get(history_url)
                data = response.json()
                
                if prompt_id in data:
                    history = data[prompt_id]
                    
                    if 'outputs' in history:
                        # Execution complete
                        task.outputs = self._parse_outputs(history['outputs'])
                        break
                        
                    # Update progress if available
                    if 'status' in history:
                        task.progress = self._parse_progress(history['status'])
                
                time.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                logger.error(f"Error polling status: {e}")
                time.sleep(5)
```

---

### 3.5 TaskManager

**File**: `app/create/task_manager.py`

**Purpose**: Manage execution tasks and their lifecycle

**Key Methods**:
```python
class TaskManager:
    _tasks = {}  # In-memory storage (use Redis in production)
    _lock = threading.Lock()
    
    @classmethod
    def register_task(cls, task_id: str, task: ExecutionTask):
        """Register a new task"""
        with cls._lock:
            cls._tasks[task_id] = task
            
    @classmethod
    def get_task(cls, task_id: str) -> Optional[ExecutionTask]:
        """Get task by ID"""
        with cls._lock:
            return cls._tasks.get(task_id)
            
    @classmethod
    def cleanup_old_tasks(cls, max_age_hours: int = 24):
        """Remove tasks older than max_age_hours"""
        with cls._lock:
            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
            to_remove = [
                task_id for task_id, task in cls._tasks.items()
                if task.started_at and task.started_at < cutoff
            ]
            for task_id in to_remove:
                del cls._tasks[task_id]

class ExecutionTask:
    def __init__(self, task_id: str, workflow_id: str, 
                 ssh_connection: str, options: dict):
        self.task_id = task_id
        self.workflow_id = workflow_id
        self.ssh_connection = ssh_connection
        self.options = options
        self.status = 'queued'
        self.started_at = datetime.utcnow()
        self.progress = {'current': 0, 'total': 0, 'percent': 0}
        self.outputs = []
        self.error = None
        self.comfyui_prompt_id = None
        self.metadata = {}
        
    def get_elapsed_seconds(self) -> int:
        """Get elapsed time in seconds"""
        if not self.started_at:
            return 0
        return int((datetime.utcnow() - self.started_at).total_seconds())
        
    def get_estimated_remaining(self) -> Optional[int]:
        """Estimate remaining time based on progress"""
        if self.progress['percent'] == 0:
            return None
        elapsed = self.get_elapsed_seconds()
        total_estimated = elapsed / (self.progress['percent'] / 100)
        return int(total_estimated - elapsed)
        
    def cancel(self):
        """Cancel the task"""
        self.status = 'cancelled'
        # Send cancel request to ComfyUI if running
        if self.comfyui_prompt_id:
            self._cancel_comfyui_prompt()
```

---

## 4. Data Models

### 4.1 WorkflowConfig
```python
@dataclass
class WorkflowConfig:
    id: str
    name: str
    description: str
    version: str
    category: str
    workflow_file: str
    vram_estimate: str
    time_estimate: dict
    layout: LayoutConfig
    inputs: List[InputConfig]
    outputs: List[OutputConfig]
    
@dataclass
class InputConfig:
    id: str
    section: str
    node_id: Optional[str]
    node_ids: Optional[List[str]]
    field: Optional[str]
    fields: Optional[List[str]]
    type: str
    label: str
    description: str
    required: bool
    default: Optional[Any]
    min: Optional[float]
    max: Optional[float]
    step: Optional[float]
    options: Optional[List[str]]
    depends_on: Optional[dict]
    model_type: Optional[str]
```

---

## 5. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create Flask blueprint structure
- [ ] Implement WorkflowLoader
- [ ] Add /workflows/list endpoint
- [ ] Add /workflows/<id> endpoint
- [ ] Test with IMG_to_VIDEO.webui.yml

### Phase 2: Generation (Week 2)
- [ ] Implement WorkflowGenerator
- [ ] Implement WorkflowValidator
- [ ] Add /generate-workflow endpoint
- [ ] Test all input types (slider, text, image, etc.)
- [ ] Test high-low pair models and LoRAs

### Phase 3: Execution (Week 3)
- [ ] Implement WorkflowExecutor
- [ ] Implement TaskManager
- [ ] Add /execute endpoint
- [ ] Add /status/<task_id> endpoint
- [ ] Test SSH upload and ComfyUI submission

### Phase 4: Polish (Week 4)
- [ ] Add /cancel/<task_id> endpoint
- [ ] Implement output file retrieval
- [ ] Add progress tracking
- [ ] Error handling and validation
- [ ] Performance optimization

### Phase 5: Integration (Week 5)
- [ ] Frontend integration testing
- [ ] End-to-end workflow execution tests
- [ ] Documentation
- [ ] Deployment

---

## 6. Testing Strategy

### Unit Tests
```python
# test_workflow_loader.py
def test_discover_workflows():
    workflows = WorkflowLoader.discover_workflows()
    assert len(workflows) > 0
    assert 'IMG_to_VIDEO' in [w.id for w in workflows]

# test_workflow_generator.py
def test_generate_simple_workflow():
    config = WorkflowLoader.load_workflow('IMG_to_VIDEO')
    template = WorkflowLoader.load_workflow_json('IMG_to_VIDEO')
    generator = WorkflowGenerator(config, template)
    
    inputs = {
        'positive_prompt': 'test prompt',
        'duration': 5.0
    }
    
    workflow = generator.generate(inputs)
    assert workflow['408']['inputs']['value'] == 'test prompt'
    assert workflow['426']['inputs']['Xi'] == 5.0

# test_workflow_validator.py
def test_validate_required_fields():
    config = WorkflowLoader.load_workflow('IMG_to_VIDEO')
    validator = WorkflowValidator(config)
    
    result = validator.validate_inputs({})
    assert not result.is_valid
    assert any('Input Image' in e['message'] for e in result.errors)
```

### Integration Tests
```python
# test_create_api.py
def test_list_workflows():
    response = client.get('/create/workflows/list')
    data = response.get_json()
    assert data['success'] == True
    assert len(data['workflows']) > 0

def test_generate_workflow():
    payload = {
        'workflow_id': 'IMG_to_VIDEO',
        'inputs': {...}
    }
    response = client.post('/create/generate-workflow', json=payload)
    data = response.get_json()
    assert data['success'] == True
    assert 'workflow' in data
```

---

## 7. Error Handling

### Common Error Scenarios
1. **Workflow not found**: Return 404 with helpful message
2. **Invalid inputs**: Return 400 with validation errors
3. **SSH connection failed**: Return 503 with connection details
4. **ComfyUI API unreachable**: Retry with exponential backoff
5. **Execution timeout**: Cancel and return timeout error
6. **Missing models**: Return 400 with list of missing requirements

### Error Response Format
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    {
      "field": "positive_prompt",
      "message": "Positive Prompt is required"
    }
  ],
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2025-11-29T12:34:56Z"
}
```

---

## 8. Security Considerations

### Input Validation
- Sanitize all user inputs
- Validate file paths (prevent directory traversal)
- Limit file upload sizes
- Validate SSH connection strings
- Rate limit API calls

### Authentication
- Require API key or session token
- Validate SSH keys before execution
- Limit concurrent executions per user

### Resource Limits
- Max workflow execution time: 1 hour
- Max concurrent tasks per user: 3
- Max workflow JSON size: 10MB
- Max uploaded image size: 50MB

---

## 9. Performance Optimization

### Caching Strategy
- Cache parsed YAML configs (5 min TTL)
- Cache workflow templates (5 min TTL)
- Cache model scan results (5 min TTL)

### Async Processing
- Use background threads for execution
- Use connection pooling for SSH
- Use Redis for task storage (production)

### Monitoring
- Track execution times
- Monitor success/failure rates
- Alert on high error rates
- Log all API calls

---

## 10. Documentation Requirements

### API Documentation
- OpenAPI/Swagger spec
- Request/response examples
- Error codes reference
- Rate limits

### Developer Guide
- How to create new workflows
- YAML config format
- Input type reference
- Component development guide

### User Guide
- Workflow execution tutorial
- Troubleshooting guide
- FAQ

---

## Success Criteria

### Functional
- ✅ All endpoints return correct responses
- ✅ Workflow generation produces valid ComfyUI JSON
- ✅ Validation catches all invalid inputs
- ✅ Execution successfully runs on remote instances
- ✅ Status polling works reliably
- ✅ Error handling is comprehensive

### Performance
- API response time < 500ms (non-execution endpoints)
- Workflow generation < 1 second
- Status polling interval: 2 seconds
- Task cleanup runs every hour

### Reliability
- 99% uptime for API
- Graceful degradation on failures
- Automatic retry for transient errors
- Proper cleanup of failed tasks
