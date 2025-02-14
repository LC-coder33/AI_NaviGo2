import google.generativeai as genai
from typing import Dict, Any
import json
from datetime import datetime
from config import GEMINI_API_KEY

class GeminiAPIHelper:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        genai.configure(api_key=api_key)
        generation_config = {
            "temperature": 0.9,
            "top_p": 1,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        self.model = genai.GenerativeModel('gemini-2.0-flash', generation_config=generation_config)

    def _clean_json_response(self, text: str) -> str:
        """Gemini 응답에서 JSON 부분만 추출"""
        if '```json' in text:
            text = text.split('```json')[1]
        if '```' in text:
            text = text.split('```')[0]
        return text.strip()

    def _format_place_info(self, travel_data: Dict[str, Any]) -> str:
        """장소 정보를 포맷팅"""
        place_info = []
        
        # 관광지 정보
        if 'attractions' in travel_data:
            for attraction in travel_data['attractions']:
                duration = attraction.get('estimated_duration', 60)
                rec_time = attraction.get('recommended_time', {'start': '10:00', 'end': '16:00'})
                info = (
                    f"- {attraction['name']}\n"
                    f"  * 추천 방문시간: {rec_time['start']}-{rec_time['end']}\n"
                    f"  * 예상 소요시간: {duration}분"
                )
                place_info.append(info)
        
        # 식당 정보
        if 'restaurants' in travel_data:
            for restaurant in travel_data['restaurants']:
                rec_time = restaurant.get('recommended_time', {
                    'lunch': {'start': '12:00', 'end': '14:00'},
                    'dinner': {'start': '18:00', 'end': '20:00'}
                })
                info = (
                    f"- {restaurant['name']} (식당)\n"
                    f"  * 점심 가능시간: {rec_time['lunch']['start']}-{rec_time['lunch']['end']}\n"
                    f"  * 저녁 가능시간: {rec_time['dinner']['start']}-{rec_time['dinner']['end']}"
                )
                place_info.append(info)
        
        return "\n".join(place_info)

    def create_travel_plan(self, travel_data: Dict[str, Any]) -> Dict[str, Any]:
        """여행 데이터를 기반으로 Gemini API를 사용하여 상세 여행 계획 생성"""
        
        json_template = """{
            "summary": {
                "main_attractions": [주요 방문지 5-6곳],
                "route_overview": "간단한 동선 설명"
            },
            "daily_schedule": [
                {
                    "day": 1,
                    "date": "YYYY-MM-DD",
                    "activities": [
                        {
                            "type": "attraction/restaurant/hotel",
                            "time": "HH:MM",
                            "place": "장소명",
                            "duration": "예상 소요시간(분)",
                            "notes": "장소에 대한 간략한 설명 및 방문 목적"
                        }
                    ],
                    "total_distance": 이동거리(km)
                }
            ]
        }"""

        start_date = datetime.strptime(travel_data['duration']['start_date'], '%Y-%m-%d')
        total_days = travel_data['duration']['total_days']

        # 장소 정보 포맷팅
        place_info = self._format_place_info(travel_data)

        safety_prompt = "반드시 유효한 JSON 형식으로 응답해주시고, 추가 설명이나 마크다운 기호는 사용하지 말아주세요."

        prompt = f"""
{safety_prompt}

여행 플래너로서 {travel_data['destination']}의 {total_days}일 일정을 한국어로 만들어주세요.

기본 정보:
- 기간: {start_date.strftime('%Y-%m-%d')}부터 {total_days}일
- 여행자: {travel_data['travelers']['count']}명 ({travel_data['travelers']['type']})

장소 정보:
{place_info}

필수 규칙:
1. 정확히 {total_days}일의 일정을 작성하세요.
2. 하루 일정은 다음과 같은 시간 순서로 구성하세요:
   - 오전(10:00-12:00): 관광지 1-2곳
   - 점심(12:00-14:00): 식당 1곳
   - 오후(14:00-18:00): 관광지 1-2곳
   - 저녁(18:00-20:00): 식당 1곳

3. 장소별 방문 시간을 준수하세요:
   - 박물관/미술관: 약 120분
   - 일반 관광지: 약 60분
   - 식사: 약 90분
   - 이동시간: 장소 간 최소 30분

4. 첫날은 비행기 도착을 고려해 14:00 이후부터 시작하고, 저녁 식사와 1-2곳만 방문하세요.

5. 마지막 날은 비행기 출발을 고려해 오전에 1곳만 방문하고 12:00 전에 일정을 마무리하세요.

6. 각 장소는 반드시 추천 방문 시간대에 맞춰 일정을 잡아주세요.

7. "time" 필드는 반드시 "HH:MM" 형식으로 입력하세요.

8. "duration" 필드는 예상 소요시간을 분 단위로 입력하세요.

{json_template}"""

        try:
            for attempt in range(2):
                try:
                    response = self.model.generate_content(prompt, stream=False)
                    cleaned_response = self._clean_json_response(response.text)
                    plan_data = json.loads(cleaned_response)
                    
                    if isinstance(plan_data, dict) and "daily_schedule" in plan_data:
                        if len(plan_data["daily_schedule"]) == total_days:
                            # 위치 정보 추가
                            for day in plan_data["daily_schedule"]:
                                for activity in day["activities"]:
                                    place_name = activity["place"]
                                    if place_name in travel_data["locations"]:
                                        activity["location"] = travel_data["locations"][place_name]
                            
                            return plan_data
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == 1:
                        raise e
            
            raise ValueError("유효한 여행 계획을 생성하지 못했습니다.")
            
        except Exception as e:
            print(f"Error generating travel plan: {str(e)}")
            return {
                "error": "여행 계획 생성에 실패했습니다.",
                "message": str(e),
                "raw_response": response.text if 'response' in locals() else None
            }