"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPFacilitiesServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def run_react_agent(user_query: str, provider, mcp_server: MCPFacilitiesServer) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp ReAct Thought -> Action -> Observation với MCP Server
    Vòng lặp tiếp tục cho đến khi LLM trả về Final Answer (type == "text") hoặc hết MAX_ITERATIONS,
    cho phép bài toán đa bước: Tra cứu (room_availability_query) -> Đặt phòng (room_booking).
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()
    transcript = [f"Người dùng: {user_query}"]
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Gọi LLM với Native Tool Calling Specs + toàn bộ transcript (lịch sử Thought/Action/Observation)
        llm_response = provider.generate_with_tools(
            "\n".join(transcript),
            tools_list,
            system_prompt=REACT_AGENT_SYSTEM_PROMPT
        )
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")
        
        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp -> Final Answer
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })
            return trace_logs
        
        # Trường hợp 2: LLM đề xuất gọi Tool (Action) -> thực thi qua MCP Server -> Observation
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            
            # Thực thi Tool qua MCP Server
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})
            obs_str = json.dumps(obs_data, ensure_ascii=False)
            
            print(f"👁️ [Observation từ MCP Server]: {obs_str}")
            
            # Ghi nhận sự kiện Tool Execution vào Trace Log
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": latency_ms
            })
            
            # Nạp Thought/Action/Observation vào transcript cho lượt suy luận kế tiếp
            transcript.append(f"Thought: {thought}")
            transcript.append(f"Action: {tool_name}({json.dumps(arguments, ensure_ascii=False)})")
            transcript.append(f"Observation: {obs_str}")
        
        else:
            break
    
    # Đạt giới hạn MAX_ITERATIONS mà vẫn chưa có Final Answer
    final_answer = (
        f"Đã đạt giới hạn {MAX_ITERATIONS} bước suy luận ReAct mà chưa hoàn tất yêu cầu. "
        "Vui lòng kiểm tra lại câu hỏi hoặc kết nối LLM API thật để có chuỗi suy luận chính xác."
    )
    print(f"🏁 [Final Answer]: {final_answer}")
    trace_logs.append({
        "step": step + 1,
        "query": user_query,
        "action_type": "FINAL_ANSWER",
        "thought": "Đã đạt giới hạn MAX_ITERATIONS của vòng lặp ReAct.",
        "output": final_answer,
        "latency_ms": 0.0
    })
    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🏢 VINGROUP AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPFacilitiesServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Chính sách đặt phòng họp quy định mỗi lần đặt tối đa bao lâu?'")
        print("   - Tra cứu phòng: 'Kiểm tra các phòng họp còn trống ngày 20/09/2026 khung giờ 14:00-15:00'")
        print("   - Đặt phòng: 'Đặt phòng họp BR-B202 lúc 09:00-10:30 ngày 21/09/2026 cho Nguyễn Văn Chiến (EMP0003)'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        while True:
            try:
                user_input = input("👤 Nhân viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []
        
        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1
                
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        if all_traces:
            save_waterfall_trace(all_traces)
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu phòng họp) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")