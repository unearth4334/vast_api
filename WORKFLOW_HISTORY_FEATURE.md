# Workflow History Feature

## Overview
This feature adds a comprehensive history tracking system to the workflow editor in the Create tab. Users can now save, browse, and restore previous workflow configurations with a single click.

## Features

### 1. Automatic History Saving
- Every workflow submission is automatically saved to history
- Includes all form inputs (text, numbers, images, model selections)
- Preserves base64 image data for complete restoration
- Tagged with workflow version hash for compatibility checking
- Includes thumbnail preview and execution metadata

### 2. Visual History Browser
- **Tiled View**: Grid layout showing workflow submissions
- **Thumbnails**: Visual preview of input images (if provided)
- **Timestamps**: Format - YY/MM/DD-HH:MM:SS
- **Pagination**: Initial 10 records, load 5 more with each "Load More" click
- **Filtering**: Only shows records matching current workflow version

### 3. One-Click Restoration
- Click any history tile to restore that workflow
- All form fields automatically populated
- Images restored with preview
- Works with complex fields (model selectors, checkboxes, etc.)

## User Guide

### Saving a Workflow to History
1. Select a workflow in the Create tab
2. Fill in all the desired inputs
3. Click "Run Workflow"
4. The workflow is automatically saved to history

### Viewing History
1. Select the same workflow you want to see history for
2. Click the "📜 History" button in the workflow editor header
3. History browser overlay appears showing past submissions

### Restoring a Previous Workflow
1. Open the history browser
2. Click on any tile to select it
3. The form automatically populates with all saved values
4. Modify if needed and run again

## Technical Details

### Architecture

#### Backend (`Python/Flask`)
- **Module**: `app/create/workflow_history.py`
- **Storage**: File-based JSON records in `data/workflow_history/`
- **API Endpoints**:
  - `GET /create/history/list` - Paginated history listing
  - `GET /create/history/<record_id>` - Specific record retrieval

#### Frontend (`JavaScript ES6`)
- **Component**: `app/webui/js/create/components/HistoryBrowser.js`
- **Integration**: `app/webui/js/create/create-tab.js`
- **Styles**: `app/webui/css/create.css`

### Data Model

Each history record contains:
```json
{
  "record_id": "20251210_143052_123456",
  "workflow_id": "IMG_to_VIDEO",
  "workflow_hash": "4df7c3cef90000f2...",
  "timestamp": "2025-12-10T14:30:52.123456",
  "inputs": {
    "positive_prompt": "...",
    "input_image": "data:image/jpeg;base64,...",
    "seed": 12345,
    "steps": 20
  },
  "thumbnail": "thumb_20251210_143052_abc12345.jpg",
  "prompt_id": "comfyui_prompt_id",
  "task_id": "uuid_task_id"
}
```

### Workflow Version Compatibility
- Each workflow file (`*.webui.yml`) has an MD5 hash computed from its content
- History records are tagged with this hash
- Only records matching the current workflow version are shown
- This prevents incompatible configurations from being loaded

## File Structure
```
app/
├── api/
│   └── create.py                      # Added history endpoints
├── create/
│   └── workflow_history.py            # New: History manager
└── webui/
    ├── css/
    │   └── create.css                 # Added history styles
    ├── js/create/
    │   ├── components/
    │   │   └── HistoryBrowser.js      # New: Browser component
    │   └── create-tab.js              # Integrated history
    └── index_template.html            # Added history button

data/
└── workflow_history/                  # New: Storage directory
    └── {timestamp}.json               # Individual records

downloads/
└── thumbnails/                        # Thumbnail storage
    └── thumb_{timestamp}_{id}.jpg
```

## Security Considerations

✅ **Implemented Security Measures:**
- XSS prevention: DOM methods used instead of innerHTML for user data
- Proper event listener cleanup to prevent memory leaks
- HTML escaping for all user-generated content
- Base64 validation for image data
- Error handling for all async operations

## Performance Considerations

**Current Implementation:**
- File-based storage (no database required)
- In-memory sorting for pagination
- Suitable for hundreds of records

**Future Optimizations** (if needed):
- Database backend (SQLite/PostgreSQL) for 1000+ records
- File-based pagination by filename sorting
- Caching layer for frequently accessed records
- Background cleanup of old records

## Testing

### Backend Tests Completed
✅ Workflow hash computation
✅ Record saving and retrieval
✅ Pagination functionality
✅ Workflow filtering by hash
✅ Record counting

### Manual Testing Required
- [ ] UI appearance and responsiveness
- [ ] History browser modal interaction
- [ ] Tile selection and form population
- [ ] Image restoration
- [ ] Load more pagination
- [ ] Different workflow types
- [ ] Large datasets (50+ records)

## Known Limitations

1. **Storage**: File-based storage may become slow with 1000+ records
2. **Images**: Large base64 images increase record file size
3. **Thumbnails**: Not automatically cleaned up (manual cleanup needed)
4. **Versions**: Changing workflow structure invalidates old records

## Future Enhancements

Potential improvements:
- 🗑️ Delete individual history records
- 🔍 Search/filter by prompt text or date range
- ⭐ Favorite/bookmark specific configurations
- 📊 Statistics dashboard (most used settings, etc.)
- 📤 Export/import history records
- 🧹 Automatic cleanup of old records
- 🏷️ Custom tags/labels for records
- 📸 Better thumbnail generation options

## Troubleshooting

### History button doesn't appear
- Check console for JavaScript errors
- Verify HistoryBrowser.js is loaded
- Ensure workflow is selected first

### History records not saving
- Check `data/workflow_history/` directory exists
- Verify write permissions
- Check server logs for errors

### Can't restore workflow
- Ensure workflow hash matches current version
- Check if all fields exist in current workflow
- Review browser console for errors

### Pagination not working
- Check network tab for API response
- Verify `has_more` flag in response
- Check for JavaScript console errors

## Support

For issues or questions:
1. Check server logs in `logs/` directory
2. Check browser console for JavaScript errors
3. Verify file permissions on `data/workflow_history/`
4. Review API responses in network tab

## Change Log

**v1.0.0** (2025-12-10)
- Initial implementation
- File-based storage
- Pagination support
- Thumbnail integration
- XSS prevention
- Memory leak fixes
