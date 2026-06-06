# Property Filter API Migration

This document describes the migration from GET-based form submission to POST-based JSON API for property filtering, similar to the React implementation.

## Changes Made

### 1. New API Endpoint

**URL**: `/api/properties/filter/`
**Method**: POST
**Content-Type**: application/json

**Request Body**:
```json
{
  "city": "Dubai",
  "district": "Downtown Dubai", 
  "property_type": "Residential",
  "unit_type": "Apartment",
  "rooms": "2",
  "delivery_year": 2025,
  "low_price": 1000000,
  "max_price": 5000000,
  "min_area": 1000,
  "max_area": 3000,
  "sales_status": "",
  "title": "Project Name",
  "developer": "Emaar",
  "property_status": "Ready"
}
```

**Response**:
```json
{
  "status": true,
  "data": {
    "results": [...],
    "count": 150,
    "current_page": 1,
    "last_page": 13,
    "next_page_url": "...",
    "prev_page_url": null
  }
}
```

### 2. Backend Changes

#### New View Function
- Added `filter_properties_api` in `main/views.py`
- Handles POST requests with JSON body
- Uses existing `PropertyService.get_properties()` method
- Returns JSON response with mapped properties

#### URL Configuration
- Added new URL pattern in `main/urls.py`
- Route: `path('api/properties/filter/', views.filter_properties_api, name='filter_properties_api')`

### 3. Frontend Changes

#### Form Updates
- Changed form method from GET to POST
- Added CSRF token
- Prevented default form submission
- Added JavaScript-based form handling

#### JavaScript Functions
- `handleSearch()`: Collects form data and makes API call
- `updatePropertiesGrid()`: Updates the properties display
- `updatePagination()`: Updates pagination controls
- `updateTotalCount()`: Updates the total count display
- `showError()`: Shows error messages
- `goToPage()`: Handles pagination with API calls

#### Key Features
- Real-time property filtering without page reload
- Dynamic pagination
- Error handling and user feedback
- Loading states
- CSRF token handling

### 4. Compatibility

The new implementation maintains backward compatibility:
- The original GET-based properties view still works
- The new API can be used independently
- Both approaches can coexist

## Testing

### Manual Testing
1. Start the Django server: `python manage.py runserver`
2. Navigate to `/properties/`
3. Use the filter form to test different combinations
4. Check browser console for API calls and responses

### Automated Testing
Run the test script:
```bash
python test_api.py
```

## API Endpoint Details

### Request Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| city | string | City name | "Dubai" |
| district | string | District/neighborhood | "Downtown Dubai" |
| property_type | string | Property type | "Residential" or "Commercial" |
| unit_type | string | Unit type | "Apartment", "Villa", etc. |
| rooms | string | Number of bedrooms | "2" |
| delivery_year | integer | Delivery year | 2025 |
| low_price | integer | Minimum price in AED | 1000000 |
| max_price | integer | Maximum price in AED | 5000000 |
| min_area | integer | Minimum area in sq ft | 1000 |
| max_area | integer | Maximum area in sq ft | 3000 |
| title | string | Project name | "Emaar Beach Vista" |
| developer | string | Developer name | "Emaar" |
| property_status | string | Property status | "Ready" or "Off Plan" |

### Response Format

The API returns a JSON response with the following structure:

```json
{
  "status": true,
  "data": {
    "results": [
      {
        "id": 123,
        "title": "Luxury Apartment",
        "location": "Dubai Marina, Dubai",
        "bedrooms": "2",
        "area": "1500",
        "price": 2500000,
        "low_price": 2500000,
        "property_type": "Premium",
        "image": "https://example.com/image.jpg",
        "detail_url": "/property/123/"
      }
    ],
    "count": 150,
    "current_page": 1,
    "last_page": 13,
    "next_page_url": "https://api.example.com/properties?page=2",
    "prev_page_url": null
  }
}
```

## Error Handling

The API includes comprehensive error handling:

- **400 Bad Request**: Invalid JSON data
- **500 Internal Server Error**: Server-side errors
- **JSON Response**: Error details in response body

Example error response:
```json
{
  "status": false,
  "error": "Invalid JSON data"
}
```

## Security

- CSRF protection enabled
- Input validation and sanitization
- Rate limiting (if configured)
- Proper error handling without exposing sensitive information

## Performance Considerations

- API calls are asynchronous
- Loading states provide user feedback
- Pagination reduces data transfer
- Caching can be implemented for frequently used filters

## Future Enhancements

1. **Caching**: Implement Redis caching for filter results
2. **Rate Limiting**: Add rate limiting for API endpoints
3. **Analytics**: Track popular filter combinations
4. **Advanced Filters**: Add more filter options
5. **Real-time Updates**: WebSocket support for real-time property updates
