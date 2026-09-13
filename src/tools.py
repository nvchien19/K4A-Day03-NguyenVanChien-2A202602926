"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from typing import Dict, Any, Optional, List

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Tra cứu tình trạng phòng họp & thiết bị (Facilities Agent)
    {
        "name": "room_availability_query",
        "description": "Tra cứu hồ sơ và tình trạng trống/bận của phòng họp cùng thiết bị văn phòng theo ngày và khung giờ cụ thể.",
        "parameters": {
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "Ngày cần tra cứu (ví dụ: '20/09/2026')"
                },
                "time_slot": {
                    "type": "string",
                    "description": "Khung giờ cần kiểm tra, định dạng 'HH:MM-HH:MM' (ví dụ: '14:00-15:00')"
                },
                "room_id": {
                    "type": "string",
                    "description": "Mã phòng họp cần tra cứu (ví dụ: 'BR-A101'). Bỏ trống để xem danh sách các phòng còn trống."
                }
            },
            "required": ["date_str", "time_slot"]
        }
    },

    # Tool 2: Đặt phòng họp & thiết bị (Facilities Agent)
    {
        "name": "room_booking",
        "description": "Đặt phòng họp và thiết bị văn phòng cho nhân viên theo ngày và khung giờ yêu cầu.",
        "parameters": {
            "type": "object",
            "properties": {
                "room_id": {
                    "type": "string",
                    "description": "Mã phòng họp cần đặt (ví dụ: 'BR-A101')"
                },
                "date_str": {
                    "type": "string",
                    "description": "Ngày cần đặt (ví dụ: '21/09/2026')"
                },
                "time_slot": {
                    "type": "string",
                    "description": "Khung giờ cần đặt, định dạng 'HH:MM-HH:MM' (ví dụ: '09:00-10:30')"
                },
                "employee_id": {
                    "type": "string",
                    "description": "Mã nhân viên đặt phòng (ví dụ: 'EMP0003')"
                },
                "booker_name": {
                    "type": "string",
                    "description": "Tên nhân viên đặt phòng (ví dụ: 'Nguyễn Văn Chiến')"
                },
                "equipment": {
                    "type": "array",
                    "description": "Danh sách thiết bị đi kèm yêu cầu (ví dụ: ['Máy chiếu', 'Loa Bluetooth'])",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": ["room_id", "date_str", "time_slot", "employee_id", "booker_name"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_ROOMS = {
    "BR-A101": {"name": "Phòng Họp A101", "capacity": 20, "equipment": ["Máy chiếu", "Bảng trắng"]},
    "BR-B202": {"name": "Phòng Họp B202", "capacity": 8, "equipment": ["TV 65 inch"]},
    "HALL-C03": {"name": "Hội trường C03", "capacity": 100, "equipment": ["Loa Bluetooth", "Máy chiếu"]}
}

MOCK_ROOM_SCHEDULE = {
    "BR-A101": {
        "20/09/2026": ["14:00-15:00"],
        "21/09/2026": ["09:00-11:00"]
    },
    "HALL-C03": {
        "20/09/2026": ["08:00-10:00"]
    }
}


def _slot_overlaps(slot_a: str, slot_b: str) -> bool:
    """Kiểm tra hai khung giờ định dạng 'HH:MM-HH:MM' có xung đột với nhau không."""
    def to_minutes(value: str) -> int:
        h, m = map(int, value.split(":"))
        return h * 60 + m
    try:
        start_a, end_a = slot_a.split("-")
        start_b, end_b = slot_b.split("-")
        return to_minutes(start_a) < to_minutes(end_b) and to_minutes(start_b) < to_minutes(end_a)
    except Exception:
        return slot_a == slot_b


def execute_room_availability_query(date_str: str, time_slot: str = "", room_id: Optional[str] = None) -> str:
    """Thực thi tra cứu tình trạng phòng họp & thiết bị theo ngày và khung giờ."""
    if room_id:
        room = MOCK_ROOMS.get(room_id.strip().upper())
        if not room:
            return json.dumps({
                "status": "NOT_FOUND",
                "room_id": room_id,
                "message": f"Không tìm thấy phòng họp có mã '{room_id}'"
            }, ensure_ascii=False)
        busy_slots = MOCK_ROOM_SCHEDULE.get(room_id.strip().upper(), {}).get(date_str, [])
        availability = "BOOKED" if time_slot and any(_slot_overlaps(time_slot, s) for s in busy_slots) else "AVAILABLE"
        return json.dumps({
            "status": "SUCCESS",
            "room_id": room_id,
            "date_str": date_str,
            "time_slot": time_slot,
            "availability": availability,
            "room_data": room,
            "busy_slots": busy_slots
        }, ensure_ascii=False)

    available_rooms = []
    for rid, room in MOCK_ROOMS.items():
        busy_slots = MOCK_ROOM_SCHEDULE.get(rid, {}).get(date_str, [])
        if not time_slot or not any(_slot_overlaps(time_slot, s) for s in busy_slots):
            available_rooms.append({**room, "room_id": rid, "busy_slots": busy_slots})
    return json.dumps({
        "status": "SUCCESS",
        "date_str": date_str,
        "time_slot": time_slot,
        "available_rooms": available_rooms
    }, ensure_ascii=False)


def execute_room_booking(
    room_id: str,
    date_str: str,
    time_slot: str,
    employee_id: str,
    booker_name: str,
    equipment: Optional[List[str]] = None
) -> str:
    """Thực thi đặt phòng họp & thiết bị văn phòng."""
    room = MOCK_ROOMS.get(room_id.strip().upper())
    if not room:
        return json.dumps({
            "status": "NOT_FOUND",
            "room_id": room_id,
            "message": f"Không tìm thấy phòng họp có mã '{room_id}'"
        }, ensure_ascii=False)

    schedule = MOCK_ROOM_SCHEDULE.setdefault(room_id.strip().upper(), {})
    busy_slots = schedule.setdefault(date_str, [])
    if any(_slot_overlaps(time_slot, s) for s in busy_slots):
        return json.dumps({
            "status": "FULL",
            "room_id": room_id,
            "time_slot": time_slot,
            "message": f"{room['name']} ({room_id}) đã được đặt trong khung giờ {time_slot} ngày {date_str}. Vui lòng chọn khung giờ hoặc phòng khác."
        }, ensure_ascii=False)

    busy_slots.append(time_slot)
    booking_id = f"BK-{room_id}-{len(busy_slots)}"
    equipment_list = equipment if equipment else room.get("equipment", [])
    return json.dumps({
        "status": "SUCCESS",
        "booking_id": booking_id,
        "room_id": room_id,
        "date_str": date_str,
        "time_slot": time_slot,
        "employee_id": employee_id,
        "booker_name": booker_name,
        "equipment": equipment_list,
        "message": f"Đặt phòng thành công: {room['name']} ({room_id}) vào {time_slot} ngày {date_str} cho {booker_name}."
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "room_availability_query": execute_room_availability_query,
    "room_booking": execute_room_booking
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)