from django.urls import path
from detection.views import upload_video, video_feed, get_bike_count

urlpatterns = [
    path("", upload_video, name="upload_video"),
    path("video_feed/", video_feed, name="video_feed"),
    path("bike_count/", get_bike_count, name="bike_count"),
]
