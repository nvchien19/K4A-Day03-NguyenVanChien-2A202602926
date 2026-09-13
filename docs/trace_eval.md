# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Nguyễn Văn Chiến
> **Mã Sinh Viên / Mã Học viên:** 2A202602926
> **Chủ đề Lựa chọn:** Trợ lý Đặt Phòng họp & Thiết bị (Facilities Agent): Quản lý tra cứu tình trạng phòng họp, thiết bị văn phòng và thực hiện đặt phòng.  

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | **5 / 5** | Để hoàn tất một yêu cầu đặt phòng, Agent phải suy luận đa bước nối tiếp: phân tích nhu cầu (thời gian, sức chứa, thiết bị) ➔ tra cứu phòng trống ➔ đối chiếu thiết bị/sức chứa ➔ thực hiện đặt phòng ➔ xác nhận kết quả. Không thể trả lời bằng 1 bước đơn lẻ. |
| **2. Tool Interaction** | **5 / 5** | Hệ thống bắt buộc kết nối MCP Server với cơ sở dữ liệu phòng họp/thiết bị văn phòng: tool `room_availability_query` để tra cứu tình trạng trống/bận và tool `room_booking` để ghi nhận đặt phòng. Thiếu Tool thì không có dữ liệu thời gian thực để trả lời. |
| **3. Dynamic Decision** | **4 / 5** | Bước tiếp theo phụ thuộc vào Observation bước trước: nếu phòng yêu cầu đã kín chỗ (FULL) Agent chủ động đề xuất phòng trống thay thế; nếu mã phòng không tồn tại (NOT_FOUND) Agent dừng lại và báo lỗi lịch sự thay vì tiếp tục đặt. |
| **4. Long Horizon Goal** | **4 / 5** | Mục tiêu "sắp xếp phòng họp phù hợp cho cuộc họp" được duy trì xuyên suốt chuỗi tra cứu ➔ lọc ➔ đặt ➔ xác nhận; tuy nhiên phạm vi chỉ trong một phiên giao dịch ngắn nên không đòi hỏi mục tiêu dài hạn nhiều phiên. |
| **TỔNG ĐIỂM AGENTIC FIT** | **18 / 20** | *Tổng điểm 18/20 > 12/20: Bài toán rất phù hợp triển khai ReAct Agent System (Cấp 3).* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật (chạy qua **OpenAI GPT-4o-mini**, Test Case TC04 — chuỗi suy luận đa bước ReAct):

```json
[
  {
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "room_availability_query",
    "arguments": {
      "date_str": "22/09/2026",
      "time_slot": "09:00-11:00"
    },
    "observation": {
      "status": "SUCCESS",
      "date_str": "22/09/2026",
      "time_slot": "09:00-11:00",
      "available_rooms": [
        {"name": "Phòng Họp A101", "capacity": 20, "equipment": ["Máy chiếu", "Bảng trắng"], "room_id": "BR-A101", "busy_slots": []},
        {"name": "Phòng Họp B202", "capacity": 8, "equipment": ["TV 65 inch"], "room_id": "BR-B202", "busy_slots": []},
        {"name": "Hội trường C03", "capacity": 100, "equipment": ["Loa Bluetooth", "Máy chiếu"], "room_id": "HALL-C03", "busy_slots": []}
      ]
    },
    "latency_ms": 2276.64
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "room_booking",
    "arguments": {
      "room_id": "BR-A101",
      "date_str": "22/09/2026",
      "time_slot": "09:00-11:00",
      "employee_id": "EMP0002",
      "booker_name": "Chị Lan",
      "equipment": ["Máy chiếu", "Bảng trắng"]
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-BR-A101-1",
      "message": "Đặt phòng thành công: Phòng Họp A101 (BR-A101) vào 09:00-11:00 ngày 22/09/2026 cho Chị Lan."
    },
    "latency_ms": 1978.71
  },
  {
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "output": "Đặt phòng thành công! Bạn đã đặt Phòng Họp A101 (BR-A101) vào ngày 22/09/2026 từ 09:00 đến 11:00 cho Chị Lan. Phòng này có sức chứa 20 người và được trang bị máy chiếu cùng bảng trắng.",
    "latency_ms": 2423.67
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` (GEMINI_API_KEY + OPENAI_API_KEY) và xác nhận Agent chạy mượt mà trên LLM API thật (OpenAI GPT-4o-mini).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 6 lượt (TC02: 1 | TC03: 2 | TC04: 2 | TC05: 1).
- **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
