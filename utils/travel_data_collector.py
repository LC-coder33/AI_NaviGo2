from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Union
from datetime import datetime

router = APIRouter()

class DestinationModel(BaseModel):
    city: str
    location: Dict[str, float]

class DatesModel(BaseModel):
    startDate: datetime
    endDate: datetime

class BudgetModel(BaseModel):
    total: int
    daily: int
    currency: str = "KRW"

class TripInfoModel(BaseModel):
    destination: DestinationModel
    dates: DatesModel
    budget: BudgetModel
    themes: List[str]
    travelers: TravelersModel

@router.post("/collect-travel-data", response_model=Dict)
async def collect_travel_data(
    trip_info: TripInfoModel
) -> Dict:
    """
    여행 계획에 필요한 모든 데이터를 비동기로 수집하고 구조화합니다.
    """
    # 1. 기본 여행 정보 구성
    trip_data = {
        "tripInfo": trip_info.dict()
    }

    # 2. 호텔 정보 수집
    hotels = await hotels_helper.search_hotels(
        location=trip_info.destination.location,
        radius=5000  # 5km 반경
    )
    
    if hotels:
        # 평점과 가격을 고려하여 상위 호텔 선택
        recommended_hotel = max(
            hotels, 
            key=lambda x: (float(x.rating) * 0.7 + 
                         (5 - int(x.price_level)) * 0.3)
        )
        
        trip_data["accommodation"] = AccommodationModel(
            hotelName=recommended_hotel.name,
            location=recommended_hotel.location,
            address=recommended_hotel.address,
            rating=recommended_hotel.rating,
            priceLevel=recommended_hotel.price_level,
            checkIn="15:00",  # 일반적인 체크인 시간
            checkOut="11:00",  # 일반적인 체크아웃 시간
            photos=recommended_hotel.photos,
            reviews=recommended_hotel.reviews
        ).dict()

    # 3. 관광지 정보 수집
    places = await place_helper.get_nearby_places(
        trip_info.destination.location,
        trip_info.themes
    )
    
    processed_places = []
    for place in places:
        details = await place_helper.get_place_details(place["place_id"])
        if not details:
            continue
            
        processed_place = PlaceModel(
            id=place["place_id"],
            name=place["name"],
            type=place.get("place_type", "관광지"),
            location=LocationModel(
                lat=place["location"]["lat"],
                lng=place["location"]["lng"]
            ),
            details={
                "address": details.address,
                "rating": place.get("rating", 0),
                "reviews_count": place.get("user_ratings_total", 0),
                "priceLevel": details.price_level,
                "estimatedDuration": 120,
                "openingHours": details.opening_hours,
            }
        )
        
        # 장소 유형별 예상 소요시간 조정
        if "museum" in place.get("types", []):
            processed_place.details["estimatedDuration"] = 180
        elif "restaurant" in place.get("types", []):
            processed_place.details["estimatedDuration"] = 90
        
        processed_places.append(processed_place.dict())

    trip_data["places"] = processed_places

    return trip_data