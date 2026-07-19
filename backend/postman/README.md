# Postman

Import [boxing-backend.postman_collection.json](/Users/blue1/Documents/Slapback/boxing-rover/backend/postman/boxing-backend.postman_collection.json) into Postman to test the backend API.

## Defaults

- `base_url`: `http://127.0.0.1:5001`
- `frame_path`: `/Users/blue1/Documents/Slapback/boxing-rover/backend/app/static/images/output2.png`

## Notes

- `Create Session` stores `session_id` automatically for later requests.
- `Send LEFT Punch Command` stores `event_id`.
- `Upload Frame (Multipart)` uses the `frame_path` variable as a local file.
- `Upload Frame (Base64 JSON)` expects you to manually set `frame_base64` first if you want a `200` there.
- `Get Debug Stream` is best opened with Postman’s raw response view since it is MJPEG.
