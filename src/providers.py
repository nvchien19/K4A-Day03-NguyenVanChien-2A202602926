"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import time
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        prompt_lower = prompt.lower()

        # Nếu transcript đã chứa Observation từ lượt trước -> tổng hợp Final Answer và dừng vòng lặp
        if "observation:" in prompt_lower:
            return {
                "type": "text",
                "content": "[Mock Agent Response]: Đã tổng hợp kết quả từ MCP Server về tình trạng phòng họp như đã quan sát ở trên. Vui lòng xem chi tiết trong phần (Observation).",
                "thought": "Đã nhận Observation từ MCP Server, tổng hợp và trả lời Final Answer."
            }

        # Mô phỏng nhận diện intent đặt phòng họp & thiết bị (Facilities Agent)
        if any(w in prompt_lower for w in ["chính sách", "quy định", "bao lâu", "quy chế", "nội quy"]):
            return {
                "type": "text",
                "content": "[Mock Agent Response]: Xin chào! Chính sách đặt phòng của công ty cho phép mỗi phòng được đặt tối đa 2 khung giờ/ngày và phải đặt trước tối thiểu 24 giờ so với lịch họp.",
                "thought": "Câu hỏi chung về chính sách đặt phòng họp, trả lời trực tiếp không cần gọi Tool."
            }
        booking_hints = ["đặt giúp", "đặt phòng", "đặt lịch phòng", "book"]
        if any(h in prompt_lower for h in booking_hints) and ("phòng" in prompt_lower or "br-" in prompt_lower or "hall-" in prompt_lower):
            return {
                "type": "tool_call",
                "tool_name": "room_booking",
                "arguments": {
                    "room_id": "BR-B202",
                    "date_str": "21/09/2026",
                    "time_slot": "09:00-10:30",
                    "employee_id": "EMP0003",
                    "booker_name": "Nguyễn Văn Chiến",
                    "equipment": ["Máy chiếu"]
                },
                "thought": "Người dùng yêu cầu đặt phòng họp. Tôi sẽ gọi tool room_booking."
            }
        elif any(h in prompt_lower for h in ["trống", "phòng họp", "kiểm tra phòng", "tình trạng phòng", "tra cứu phòng"]):
            arguments = {"date_str": "20/09/2026", "time_slot": "14:00-15:00"}
            for code in ["BR-A101", "BR-B202", "HALL-C03", "HALL-Z99"]:
                if code.lower() in prompt_lower:
                    arguments["room_id"] = code
                    break
            return {
                "type": "tool_call",
                "tool_name": "room_availability_query",
                "arguments": arguments,
                "thought": "Người dùng muốn tra cứu tình trạng phòng họp. Tôi sẽ gọi tool room_availability_query."
            }
        else:
            return {
                "type": "text",
                "content": "[Mock Agent Response]: Xin chào! Chính sách đặt phòng của công ty cho phép mỗi phòng được đặt tối đa 2 khung giờ/ngày và phải đặt trước tối thiểu 24 giờ so với lịch họp.",
                "thought": "Câu hỏi chung về chính sách đặt phòng họp, trả lời trực tiếp không cần gọi Tool."
            }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-3.6-flash"
        self._max_retries = 4
        self._retry_delay = 15

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            for attempt in range(self._max_retries + 1):
                try:
                    response = client.models.generate_content(model=self.model_name, contents=contents)
                    return response.text
                except Exception as e:
                    if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt < self._max_retries:
                        print(f"⏳ [Gemini API] Rate limit (429) - chờ {self._retry_delay}s rồi thử lại (lần {attempt + 1}/{self._max_retries}) ...")
                        time.sleep(self._retry_delay)
                        continue
                    raise e
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )
        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể chuẩn bị API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        for attempt in range(self._max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )

                # Kiểm tra xem Gemini có trả về Tool Call không
                if response.function_calls:
                    call = response.function_calls[0]
                    args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                    return {
                        "type": "tool_call",
                        "tool_name": call.name,
                        "arguments": args,
                        "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                    }
                else:
                    return {
                        "type": "text",
                        "content": response.text or "",
                        "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                    }
            except Exception as e:
                msg = str(e)
                if ("429" in msg or "RESOURCE_EXHAUSTED" in msg) and attempt < self._max_retries:
                    print(f"⏳ [Gemini API] Rate limit (429) - chờ {self._retry_delay}s rồi thử lại (lần {attempt + 1}/{self._max_retries}) ...")
                    time.sleep(self._retry_delay)
                    continue
                print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({msg}). Tự động fallback về Mock.")
                return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        print("⚠️ [Gemini API Warning]: Đã hết số lần retry. Tự động fallback về Mock.")
        return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages, timeout=90)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                timeout=90
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
