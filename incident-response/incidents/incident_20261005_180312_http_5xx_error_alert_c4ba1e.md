# Incident Report: incident_20261005_180312_http_5xx_error_alert_c4ba1e

## Summary
- **Alert Name**: `HTTP 5xx Error Alert`
- **Status**: `FIRING`
- **Severity**: `critical`
- **Affected Endpoint**: `/api/orders/{order_id}`
- **Timestamp**: `2026-10-05T18:03:12.640010+00:00`
- **Description**: Endpoint /api/orders/{order_id} returned 5xx responses in the last 5 minutes. Dashboard: http://localhost:3000/d/order-tracker-metrics/order-tracker-requests-and-errors
- **Dashboard**: [http://localhost:3000/d/order-tracker-metrics/order-tracker-requests-and-errors](http://localhost:3000/d/order-tracker-metrics/order-tracker-requests-and-errors)

---

## Root Cause & Diagnostics
### Detected Exceptions in Logs
- **Exception Type**: `ValueError`
- **Message**: `day is out of range for month`
```python
Traceback (most recent call last):
  File "/app/app/main.py", line 174, in get_order
    return order_detail(row)
           ^^^^^^^^^^^^^^^^^
  File "/app/app/main.py", line 67, in order_detail
    estimated_at = placed_at.replace(day=placed_at.day + 2)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: day is out of range for month
```
- **Exception Type**: `ValueError`
- **Message**: `day is out of range for month`
```python
Traceback (most recent call last):
  File "/app/app/main.py", line 174, in get_order
    return order_detail(row)
           ^^^^^^^^^^^^^^^^^
  File "/app/app/main.py", line 67, in order_detail
    estimated_at = placed_at.replace(day=placed_at.day + 2)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: day is out of range for month
```
- **Exception Type**: `ValueError`
- **Message**: `day is out of range for month`
```python
Traceback (most recent call last):
  File "/app/app/main.py", line 174, in get_order
    return order_detail(row)
           ^^^^^^^^^^^^^^^^^
  File "/app/app/main.py", line 67, in order_detail
    estimated_at = placed_at.replace(day=placed_at.day + 2)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: day is out of range for month
```
- **Exception Type**: `ValueError`
- **Message**: `day is out of range for month`
```python
Traceback (most recent call last):
  File "/app/app/main.py", line 174, in get_order
    return order_detail(row)
           ^^^^^^^^^^^^^^^^^
  File "/app/app/main.py", line 67, in order_detail
    estimated_at = placed_at.replace(day=placed_at.day + 2)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: day is out of range for month
```
- **Exception Type**: `ValueError`
- **Message**: `day is out of range for month`
```python
Traceback (most recent call last):
  File "/app/app/main.py", line 174, in get_order
    return order_detail(row)
           ^^^^^^^^^^^^^^^^^
  File "/app/app/main.py", line 67, in order_detail
    estimated_at = placed_at.replace(day=placed_at.day + 2)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: day is out of range for month
```

---

## Distributed Traces (17 captured)
### Trace `39df81422a39046ebf4e952d2fd0f64c` ✅ [OK]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 4.5 | `200` | `/api/orders/{order_id}` | No |

### Trace `f272c80fc36e1fbdf27ff26d44aa87a5` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 1.7 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `bb6040d06781b1e525ca80b5c272045d` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 1.56 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `1e0fa4ff9d4e73264fcbe454b6c0c6f0` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 2.86 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `ae539f89819b69b28e77a08ee5557898` ✅ [OK]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `list_orders` | 15.63 | `200` | `/api/orders` | No |

### Trace `1a2cf97defc3a474547e8392f91f37e6` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 31.04 | `404` | `/api/orders/{order_id}` | HTTPException: 404: Order not found |

### Trace `d84ff99f7961000dbac5520d6e5c5e02` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 1.91 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `61d6cd1f5491034fe188dad8a3beca7f` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 2.36 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `c2aeff962e550dbd81e66a97aa544514` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 4.33 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `49c61e1fb0552d794e6d36272f45bed5` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 1.97 | `404` | `/api/orders/{order_id}` | HTTPException: 404: Order not found |

### Trace `77a0a7c015b86bc5285cdbc30fd83915` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 2.23 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `d017aa9ff1edaa919383a1f782e549b7` ✅ [OK]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 20.7 | `200` | `/api/orders/{order_id}` | No |

### Trace `94b076a1912503b5c0e3c2912d5f5537` ✅ [OK]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 8.47 | `200` | `/api/orders/{order_id}` | No |

### Trace `25858ce4dde1e8d762cb64a633d5d8ba` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 3.68 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `fc91ab1f15cf1beddffa227a76cd29a7` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 42.83 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `f701c2178d378a2f55ae7ae9f9f93b2f` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 2.88 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |

### Trace `7b52c45ea97eeda48a2dbdf54a9a4a25` ⚠️ [ERROR]
- Total Spans: 1

| Span Name | Duration (ms) | Status Code | Route | Error |
|---|---|---|---|---|
| `order_lookup` | 2.67 | `500` | `/api/orders/{order_id}` | ValueError: day is out of range for month |


---

## Application Logs (45 total, 13 errors/warnings)
| Timestamp | Level | Message | Source | Trace ID |
|---|---|---|---|---|
| 2026-10-05T17:36:17 | `INFO` | Looking up order: express-1002 | `main.py:156` | `f701c217...` |
| 2026-10-05T17:36:17 | `INFO` | Found order express-1002: status=preparing, priority=express | `main.py:172` | `f701c217...` |
| 2026-10-05T17:36:17 | `ERROR` | Error retrieving order details for express-1002: day is out of range for month | `main.py:179` | `f701c217...` |
| 2026-10-05T17:36:17 | `INFO` | Looking up order: express-1002 | `main.py:156` | `bb6040d0...` |
| 2026-10-05T17:36:17 | `INFO` | Found order express-1002: status=preparing, priority=express | `main.py:172` | `bb6040d0...` |
| 2026-10-05T17:36:17 | `ERROR` | Error retrieving order details for express-1002: day is out of range for month | `main.py:179` | `bb6040d0...` |
| 2026-10-05T17:36:17 | `INFO` | Looking up order: express-1002 | `main.py:156` | `61d6cd1f...` |
| 2026-10-05T17:36:17 | `INFO` | Found order express-1002: status=preparing, priority=express | `main.py:172` | `61d6cd1f...` |
| 2026-10-05T17:36:17 | `ERROR` | Error retrieving order details for express-1002: day is out of range for month | `main.py:179` | `61d6cd1f...` |
| 2026-10-05T17:36:17 | `INFO` | Looking up order: express-1002 | `main.py:156` | `7b52c45e...` |
| 2026-10-05T17:36:17 | `INFO` | Found order express-1002: status=preparing, priority=express | `main.py:172` | `7b52c45e...` |
| 2026-10-05T17:36:17 | `ERROR` | Error retrieving order details for express-1002: day is out of range for month | `main.py:179` | `7b52c45e...` |
| 2026-10-05T17:36:17 | `INFO` | Looking up order: express-1002 | `main.py:156` | `1e0fa4ff...` |
| 2026-10-05T17:36:17 | `INFO` | Found order express-1002: status=preparing, priority=express | `main.py:172` | `1e0fa4ff...` |
| 2026-10-05T17:36:17 | `ERROR` | Error retrieving order details for express-1002: day is out of range for month | `main.py:179` | `1e0fa4ff...` |
| 2026-10-05T17:36:18 | `INFO` | Looking up order: express-1002 | `main.py:156` | `f272c80f...` |
| 2026-10-05T17:36:18 | `INFO` | Found order express-1002: status=preparing, priority=express | `main.py:172` | `f272c80f...` |
| 2026-10-05T17:36:18 | `ERROR` | Error retrieving order details for express-1002: day is out of range for month | `main.py:179` | `f272c80f...` |
| 2026-10-05T17:36:18 | `INFO` | Looking up order: express-1002 | `main.py:156` | `d84ff99f...` |
| 2026-10-05T17:36:18 | `INFO` | Found order express-1002: status=preparing, priority=express | `main.py:172` | `d84ff99f...` |
| 2026-10-05T17:36:18 | `ERROR` | Error retrieving order details for express-1002: day is out of range for month | `main.py:179` | `d84ff99f...` |
| 2026-10-05T17:41:28 | `INFO` | Looking up order: standard-1002 | `main.py:156` | `1a2cf97d...` |
| 2026-10-05T17:41:28 | `WARN` | Order not found: standard-1002 | `main.py:164` | `1a2cf97d...` |
| 2026-10-05T17:41:41 | `INFO` | Looking up order: standard-1001 | `main.py:156` | `39df8142...` |
| 2026-10-05T17:41:41 | `INFO` | Found order standard-1001: status=received, priority=standard | `main.py:172` | `39df8142...` |
