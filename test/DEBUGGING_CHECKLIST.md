# Workflow Generation Debugging Checklist

Use this checklist when workflow generation issues occur.

## Quick Diagnosis

Run the test fixture first:
```bash
cd /home/sdamk/dev/vast_api
python3 test/test_img_to_video_canvas_workflow.py
```

If tests pass ✅ but production fails, the issue is likely in:
- Frontend data formatting
- API request handling
- Instance communication

If tests fail ✗, use this checklist to diagnose.

---

## 🔍 Issue: Token Not Replaced

**Symptom:** Generated workflow contains `{{MY_TOKEN}}` instead of actual value

### Check 1: Token Exists in Template
```bash
grep "MY_TOKEN" workflows/IMG_to_VIDEO_canvas.json
```
- ✅ Found: Token is in template
- ❌ Not found: Add token to workflow JSON

### Check 2: Token Defined in Config
```bash
grep "MY_TOKEN" workflows/IMG_to_VIDEO_canvas.webui.yml
```
Look for:
```yaml
- id: "my_input"
  token: "{{MY_TOKEN}}"  # Must match exactly (case-sensitive)
```
- ✅ Found: Config has token mapping
- ❌ Not found: Add token to input definition

### Check 3: Input Value Provided
Check test inputs or API request includes the value:
```python
"my_input": "test_value"  # Must match input ID from config
```

### Check 4: Token Format
Tokens must be:
- In double quotes: `"{{TOKEN}}"` not `{{TOKEN}}`
- All caps: `{{MY_TOKEN}}` not `{{my_token}}`
- Underscores only: `{{MY_TOKEN}}` not `{{MY-TOKEN}}`

### Fix Steps
1. Add token to workflow JSON: `"{{MY_TOKEN}}"`
2. Add token mapping to config YAML:
   ```yaml
   - id: "my_input"
     token: "{{MY_TOKEN}}"
   ```
3. Ensure input value is provided in test/request

---

## 🔍 Issue: Node Mode Not Changed

**Symptom:** Node mode stays at default instead of input value

### Check 1: Input Type Correct
```yaml
- id: "my_toggle"
  type: "node_mode_toggle"  # Must be this exact type
```

### Check 2: Node IDs Listed
```yaml
- id: "my_toggle"
  type: "node_mode_toggle"
  node_ids:
    - "447"  # Can be string or int
    - "444"
```

### Check 3: Input Value Valid
Mode values must be:
- `0` = Enabled/Active
- `2` = Disabled/Bypassed
- `4` = Muted/Inactive

### Check 4: Node Exists in Workflow
```bash
grep '"id": 447' workflows/IMG_to_VIDEO_canvas.json
```

### Fix Steps
1. Verify type is `node_mode_toggle`
2. Add node IDs to `node_ids` array
3. Ensure input value is 0, 2, or 4
4. Check node ID exists in workflow JSON

---

## 🔍 Issue: Model Path Not Set

**Symptom:** Model loader has wrong path or default value

### Check 1: Token in Workflow
```bash
grep "WAN_HIGH_MODEL" workflows/IMG_to_VIDEO_canvas.json
```
Should find: `"{{WAN_HIGH_MODEL}}"`

### Check 2: Config for Model Type
For high/low pairs:
```yaml
- id: "main_model"
  type: "high_low_pair_model"
  tokens:
    high: "{{WAN_HIGH_MODEL}}"
    low: "{{WAN_LOW_MODEL}}"
```

For single models:
```yaml
- id: "clip_model"
  type: "single_model"
  token: "{{CLIP_MODEL}}"
```

### Check 3: Input Format
High/low pair:
```python
"main_model": {
    "highNoisePath": "path/to/high/model.safetensors",
    "lowNoisePath": "path/to/low/model.safetensors"
}
```

Single model:
```python
"clip_model": {
    "path": "path/to/model.safetensors"
}
```

### Fix Steps
1. Add model token to workflow JSON
2. Configure input with correct type
3. Provide input in correct format (dict with path/highNoisePath/lowNoisePath)

---

## 🔍 Issue: Widget Value Wrong

**Symptom:** Node widget has unexpected value

### Check 1: Token Position
Find the node and check widget index:
```bash
grep -A 20 '"id": 408' workflows/IMG_to_VIDEO_canvas.json
```

Look at `widgets_values` array:
```json
"widgets_values": [
  "{{POSITIVE_PROMPT}}",  // Index 0
  "other_value"           // Index 1
]
```

### Check 2: Token in Correct Position
Token must be in the widget index you want to replace:
- If prompt is `widgets_values[0]`, token must be at index 0

### Check 3: Token Type Matches Value Type
- Text values: Use `_replace_text_token()`
- Numbers: Use `_replace_numeric_token()`
- Booleans: Use `_replace_boolean_token()`

### Fix Steps
1. Verify token is in correct widget index
2. Ensure token type matches value type
3. Check input provides value of correct type

---

## 🔍 Issue: Structure Changed

**Symptom:** Node/link counts don't match template

### Check 1: Template Not Modified
```bash
cd /home/sdamk/dev/vast_api
git diff workflows/IMG_to_VIDEO_canvas.json
```

### Check 2: Generation Adds/Removes Nodes
Check `WorkflowGenerator` for any code that modifies structure:
- Should only modify values, not add/remove nodes

### Fix Steps
1. Restore template if accidentally modified
2. Ensure generator only updates values, not structure

---

## 🔍 Issue: Invalid JSON Output

**Symptom:** Generated workflow can't be parsed

### Check 1: JSON Syntax
```bash
python3 -m json.tool test/output/IMG_to_VIDEO_canvas_generated.json
```

### Check 2: Token Replacement Broke JSON
Look for:
- Unescaped quotes in text values
- Missing commas
- Trailing commas

### Check 3: Value Escaping
Text tokens should use `json.dumps()`:
```python
workflow_str.replace(f'"{config.token}"', json.dumps(text_value))
```

### Fix Steps
1. Use `json.dumps()` for all value replacements
2. Don't manually escape strings
3. Test with values containing special characters

---

## 🔍 Issue: Test Passes, Production Fails

**Symptom:** Test fixture passes but real workflow generation fails

### Check 1: Input Format Difference
Test inputs might not match frontend format:
```python
# Test format
"input_image": "test_image.png"

# Frontend format
"input_image": "data:image/jpeg;base64,..."
```

### Check 2: API Request Parsing
Check `create_api.py` for input transformation:
```python
def generate_workflow():
    data = request.json
    # Check how inputs are extracted/transformed
```

### Check 3: Model Selection Format
Frontend might send different structure:
```javascript
// Frontend
{model: {id: "123", path: "..."}}

// Expected
{path: "..."}
```

### Fix Steps
1. Log actual API request data
2. Compare with test input format
3. Add transformation in API handler if needed

---

## 🔍 Issue: Wrong Input Applied

**Symptom:** Input value goes to wrong node or field

### Check 1: Token Uniqueness
```bash
grep -c "MY_TOKEN" workflows/IMG_to_VIDEO_canvas.json
```
If count > 1, token is reused (this is OK - all instances get same value)

### Check 2: Node ID Conflicts
Multiple inputs using same node ID:
```yaml
- id: "input1"
  node_ids: ["447"]
- id: "input2"
  node_ids: ["447"]  # Conflict!
```

### Fix Steps
1. Use unique node IDs for different inputs
2. Or use token-based replacement instead of node-based

---

## 🛠️ Debugging Tools

### 1. Inspect Generated Workflow
```bash
cat test/output/IMG_to_VIDEO_canvas_generated.json | jq . | less
```

### 2. Find Token Occurrences
```bash
grep -n "{{.*}}" test/output/IMG_to_VIDEO_canvas_generated.json
```

### 3. Compare with Example
```bash
diff <(jq . ~/Downloads/WAN2.2_IMG_to_VIDEO_Base\ \(example\).json) \
     <(jq . test/output/IMG_to_VIDEO_canvas_generated.json)
```

### 4. Check Specific Node
```bash
cat test/output/IMG_to_VIDEO_canvas_generated.json | \
  jq '.nodes[] | select(.id == 408)'
```

### 5. Count Tokens in Template
```bash
grep -o "{{[A-Z_]*}}" workflows/IMG_to_VIDEO_canvas.json | sort | uniq -c
```

### 6. Validate JSON
```bash
python3 -c "import json; json.load(open('test/output/IMG_to_VIDEO_canvas_generated.json'))"
```

---

## 📊 Quick Reference

### Token Replacement Methods
| Input Type | Method | Token Format |
|-----------|--------|--------------|
| text/textarea | `_replace_text_token()` | `"{{TOKEN}}"` |
| slider | `_replace_numeric_token()` | `"{{TOKEN}}"` |
| seed | `_replace_seed_token()` | `"{{TOKEN}}"` |
| toggle/checkbox | `_replace_boolean_token()` | `"{{TOKEN}}"` |
| high_low_pair_model | `_replace_high_low_model_tokens()` | `tokens: {high, low}` |
| single_model | `_replace_single_model_token()` | `token: "{{TOKEN}}"` |
| node_mode_toggle | (node-based, not token) | `node_ids: [...]` |

### Node Mode Values
| Mode | Meaning | Use Case |
|------|---------|----------|
| 0 | Enabled/Active | Normal execution |
| 2 | Disabled/Bypassed | Skip this node |
| 4 | Muted/Inactive | Disabled but different |

### Input Value Formats
| Type | Format | Example |
|------|--------|---------|
| Text | String | `"my text"` |
| Number | Int/Float | `42` or `3.5` |
| Seed | Int | `42` or `-1` (random) |
| Image | String | `"filename.png"` or `"data:image/..."` |
| High/Low Model | Dict | `{highNoisePath: "...", lowNoisePath: "..."}` |
| Single Model | Dict | `{path: "..."}` |
| Node Mode | Int | `0`, `2`, or `4` |

---

## 🆘 Getting More Help

1. **Check logs:**
   ```bash
   tail -f logs/app.log
   ```

2. **Run test with verbose output:**
   ```bash
   python3 test/test_img_to_video_canvas_workflow.py 2>&1 | tee test_output.log
   ```

3. **Compare working vs broken:**
   - Save working generated workflow
   - Compare with broken workflow
   - Find the difference

4. **Review documentation:**
   - [FEATURE_TOKEN_BASED_WORKFLOW_SYSTEM.md](../docs/FEATURE_TOKEN_BASED_WORKFLOW_SYSTEM.md)
   - [GUIDE_TOKEN_WORKFLOW_CREATION.md](../docs/GUIDE_TOKEN_WORKFLOW_CREATION.md)
   - [README_WORKFLOW_TESTS.md](README_WORKFLOW_TESTS.md)

5. **Check source code:**
   - `app/create/workflow_generator.py` - Token replacement logic
   - `app/create/workflow_loader.py` - Config parsing
   - `app/sync/create_api.py` - API request handling

---

## ✅ Verification Checklist

Before considering the issue fixed:

- [ ] Test fixture passes all tests
- [ ] Generated workflow loads in ComfyUI without errors
- [ ] All expected tokens are replaced
- [ ] All node modes are correct
- [ ] All model paths are valid
- [ ] All widget values match inputs
- [ ] Structure matches template
- [ ] JSON is valid
- [ ] Production API works
- [ ] Frontend receives correct workflow

---

## 📝 Common Fixes Summary

| Issue | Quick Fix |
|-------|-----------|
| Token not replaced | Add token to both JSON and YAML |
| Node mode wrong | Use `node_mode_toggle` type, provide mode value |
| Model path wrong | Check input format has `path` or `highNoisePath`/`lowNoisePath` |
| Widget value wrong | Verify token is in correct widget index |
| Invalid JSON | Use `json.dumps()` for replacements |
| Test pass, prod fails | Check input format differences in API |
