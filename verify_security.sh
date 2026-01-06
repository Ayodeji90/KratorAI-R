#!/bin/bash
# Security Verification Test Script for KratorAI Backend

set -e

echo "=================================================="
echo "KratorAI Backend Security Verification"
echo "=================================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found"
    echo "Please create a .env file with KRATORAI_BACKEND_TOKEN"
    exit 1
fi

# Extract token from .env
TOKEN=$(grep KRATORAI_BACKEND_TOKEN .env | cut -d '=' -f2 | tr -d ' ')

if [ -z "$TOKEN" ]; then
    echo "❌ ERROR: KRATORAI_BACKEND_TOKEN not set in .env file"
    echo "Please add: KRATORAI_BACKEND_TOKEN=your-token-here"
    exit 1
fi

echo "✅ Found token in .env file"
echo ""

# Check if server is running
echo "🔍 Checking if server is running on http://localhost:8000..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ ERROR: Server is not running"
    echo "Please start the server with: uvicorn src.api.main:app --reload"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Test 1: Health endpoint (should be public)
echo "=================================================="
echo "Test 1: Health Check (Public Endpoint)"
echo "=================================================="
RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$RESPONSE" | grep -q "healthy"; then
    echo "✅ PASS: Health endpoint is accessible without authentication"
else
    echo "❌ FAIL: Health endpoint not working properly"
    echo "Response: $RESPONSE"
fi
echo ""

# Test 2: Unauthenticated request (should fail with 401)
echo "=================================================="
echo "Test 2: Unauthenticated Request (Should Fail)"
echo "=================================================="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/describe \
    -F "image_url=https://example.com/image.jpg")

if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ PASS: Unauthenticated request rejected with 401"
else
    echo "❌ FAIL: Expected 401, got $HTTP_CODE"
fi
echo ""

# Test 3: Invalid token (should fail with 403)
echo "=================================================="
echo "Test 3: Invalid Token (Should Fail with 403)"
echo "=================================================="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/describe \
    -H "Authorization: Bearer invalid-token-12345" \
    -F "image_url=https://example.com/image.jpg")

if [ "$HTTP_CODE" = "403" ]; then
    echo "✅ PASS: Invalid token rejected with 403"
else
    echo "❌ FAIL: Expected 403, got $HTTP_CODE"
fi
echo ""

# Test 4: Valid token (should accept request)
echo "=================================================="
echo "Test 4: Valid Token (Should Accept)"
echo "=================================================="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/describe \
    -H "Authorization: Bearer $TOKEN" \
    -F "image_url=https://example.com/image.jpg")

# Accept 200, 400, or 500 (as long as it's not 401 or 403)
if [ "$HTTP_CODE" != "401" ] && [ "$HTTP_CODE" != "403" ]; then
    echo "✅ PASS: Valid token accepted (HTTP $HTTP_CODE)"
    echo "Note: $HTTP_CODE may indicate image processing error, which is expected"
else
    echo "❌ FAIL: Valid token was rejected with $HTTP_CODE"
fi
echo ""

# Test 5: CORS headers
echo "=================================================="
echo "Test 5: CORS Configuration"
echo "=================================================="
CORS_RESPONSE=$(curl -s -I -X OPTIONS http://localhost:8000/describe \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Authorization,Content-Type")

if echo "$CORS_RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
    echo "✅ PASS: CORS headers present"
else
    echo "⚠️  WARNING: CORS headers not found (may need to check configuration)"
fi
echo ""

# Test 6: Prompt validation (prompt too long)
echo "=================================================="
echo "Test 6: Prompt Validation (Should Reject Long Prompt)"
echo "=================================================="
LONG_PROMPT=$(python3 -c "print('a' * 2001)")
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/refine/upload \
    -H "Authorization: Bearer $TOKEN" \
    -F "prompt=$LONG_PROMPT" \
    -F "image_url=https://example.com/image.jpg")

if [ "$HTTP_CODE" = "400" ]; then
    echo "✅ PASS: Long prompt rejected with 400"
else
    echo "⚠️  WARNING: Expected 400 for long prompt, got $HTTP_CODE"
fi
echo ""

# Test 7: API info endpoint (should be public)
echo "=================================================="
echo "Test 7: API Info Endpoint (Public)"
echo "=================================================="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ PASS: API info endpoint accessible without authentication"
else
    echo "❌ FAIL: API info endpoint returned $HTTP_CODE"
fi
echo ""

# Summary
echo "=================================================="
echo "Verification Summary"
echo "=================================================="
echo "✅ All critical security tests completed"
echo ""
echo "Next Steps:"
echo "1. Configure CORS_ORIGINS in .env with your frontend domain(s)"
echo "2. Share the KRATORAI_BACKEND_TOKEN with your frontend team"
echo "3. Test integration with the actual frontend application"
echo "4. Monitor rate limiting in production"
echo ""
echo "For detailed setup instructions, see SECURITY_SETUP.md"
echo "=================================================="
