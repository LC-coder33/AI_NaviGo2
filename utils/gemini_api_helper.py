import google.generativeai as genai
from typing import Dict, Optional
import json
from datetime import datetime, timedelta
from config import GEMINI_API_KEY, GEMINI_MODEL

class GeminiAPIHelper:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={
                'max_output_tokens': 8192,
                'temperature': 0.7,
                'top_p': 0.8,
                'top_k': 40
            }
        )

    def create_travel_plan(self, travel_data: Dict) -> Optional[Dict]:
        """Gemini API를 사용하여 여행 계획을 생성합니다."""
        try:
            prompt = self._create_simple_prompt(travel_data)
            
            # API 호출
            response = self.model.generate_content(prompt)
            
            # 응답 정제
            text = response.text.strip()
            
            # 코드 블록 마커 제거
            if text.startswith('```'):
                text = text.split('\n', 1)[1]
            if text.endswith('```'):
                text = text.rsplit('\n', 1)[0]
            if text.startswith('json'):
                text = text.split('\n', 1)[1]
            
            # 디버깅을 위한 로그
            print("=== 정제된 응답 ===")
            print(text)
            print("==================")
            
            # JSON 구조가 맞는지 확인하고 필요시 보정
            if not text.startswith('{"daily_plans":'):
                text = '{"daily_plans": [' + text.strip().rstrip(',') + ']}'
            
            try:
                # JSON 파싱
                plan_data = json.loads(text)
                
                # 디버깅을 위한 로그
                print("=== 파싱된 데이터 구조 ===")
                print(json.dumps(plan_data, indent=2, ensure_ascii=False))
                print("=========================")
                
                return plan_data
                
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 오류: {e}")
                print(f"파싱 시도한 텍스트: {text}")
                # JSON 구조 복구 시도
                try:
                    # 객체 사이에 콤마 추가
                    fixed_text = text.replace('}{', '},{')
                    # 누락된 닫는 괄호 추가
                    if not fixed_text.endswith('}'):
                        fixed_text += '}'
                    if not fixed_text.endswith(']}'):
                        fixed_text += ']}'
                    plan_data = json.loads(fixed_text)
                    return plan_data
                except:
                    return {"error": "JSON 파싱 실패", "raw_response": text}
                    
        except Exception as e:
            print(f"API 호출 오류: {str(e)}")
            return None

    def _create_simple_prompt(self, travel_data: Dict) -> str:
        """여행 계획 생성을 위한 프롬프트를 생성합니다."""
        destination = travel_data["tripInfo"]["destination"]
        dates = travel_data["tripInfo"]["dates"]
        
        # 날짜 계산
        start_date = datetime.strptime(dates['startDate'], "%Y-%m-%d")
        end_date = datetime.strptime(dates['endDate'], "%Y-%m-%d")
        duration = (end_date - start_date).days
        
        prompt = f"""정확히 {duration}일 동안의 여행 일정을 JSON 형식으로 생성해주세요.

여행 정보:
- 목적지: {destination['city']}
- 여행 기간: {dates['startDate']} ~ {dates['endDate']} ({duration}일)
- 테마: {', '.join(travel_data['tripInfo']['themes'])}

숙소: {travel_data['accommodation']['hotelName']}

방문 가능한 장소:"""

        # 주요 장소들만 간단히 나열
        for place in travel_data["places"][:20]:
            prompt += f"\n- {place['name']}"

        prompt += f"""

다음과 같은 정확한 JSON 형식으로 응답해주세요:

{{
  "daily_plans": [
    // 첫째 날 (도착일)
    {{
      "day": 1,
      "date": "{dates['startDate']}",
      "meals": {{
        "breakfast": {{"location": "이동중", "time": "이동중"}},
        "lunch": {{"location": "이동중", "time": "이동중"}},
        "dinner": {{"location": "장소명", "time": "19:00"}}
      }},
      "activities": [
        {{
          "place": "호텔 체크인 및 주변 散책",
          "start_time": "17:00",
          "end_time": "18:30",
          "notes": "호텔 체크인 후 주변 구경"
        }}
      ]
    }},
    
    // 중간 일정 예시
    {{
      "day": 2,
      "date": "YYYY-MM-DD",
      "meals": {{
        "breakfast": {{"location": "{travel_data['accommodation']['hotelName']}", "time": "07:00-09:00"}},
        "lunch": {{"location": "장소명", "time": "12:30"}},
        "dinner": {{"location": "장소명", "time": "19:00"}}
      }},
      "activities": [
        {{
          "place": "장소명",
          "start_time": "09:30",
          "end_time": "11:30",
          "notes": "설명"
        }},
        {{
          "place": "장소명",
          "start_time": "13:30",
          "end_time": "16:30",
          "notes": "설명"
        }}
      ]
    }},
    
    // 마지막 날 (출국일)
    {{
      "day": {duration},
      "date": "{end_date.strftime('%Y-%m-%d')}",
      "meals": {{
        "breakfast": {{"location": "{travel_data['accommodation']['hotelName']}", "time": "07:00-09:00"}},
        "lunch": {{"location": "장소명", "time": "12:00"}},
        "dinner": {{"location": "이동중", "time": "이동중"}}
      }},
      "activities": [
        {{
          "place": "마지막 관광",
          "start_time": "09:30",
          "end_time": "11:30",
          "notes": "호텔 근처에서 가벼운 관광"
        }}
      ]
    }}
  ]
}}

주의사항:
1. 반드시 위 JSON 형식을 정확히 따라주세요. 중첩 구조 없이 "daily_plans" 배열 안에 일자별 계획 객체들을 나열해주세요.
2. 첫날은 저녁식사와 가벼운 주변 산책 정도만 계획해주세요
3. 마지막 날은 오전 관광과 점심식사까지만 계획해주세요 
4. 중간 일정은 점심 식사와 저녁 식사를 포함한 하루 5곳 정도 방문하고, 이동시간을 고려해주세요
5. 아침은 항상 호텔 조식으로 계획해주세요 (첫날 제외)  
6. 점심은 12-14시, 저녁은 18-20시 사이로 계획해주세요

JSON 형식의 여행 계획만 응답해주세요.
"""

        return prompt

    def regenerate_plan(self, travel_data: Dict, feedback: str) -> Optional[Dict]:
        """피드백을 반영하여 새로운 계획을 생성합니다."""
        prompt = self._create_simple_prompt(travel_data)
        prompt += f"\n\n다음 피드백을 반영해주세요:\n{feedback}"
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            if not text.startswith('{"daily_plans":'):
                text = '{"daily_plans": [' + text.strip().rstrip(',') + ']}'
            
            return json.loads(text)
        except Exception as e:
            print(f"계획 재생성 오류: {str(e)}")
            return None