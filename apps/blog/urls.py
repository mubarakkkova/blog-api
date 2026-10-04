from rest_framework.routers import DefaultRouter

from apps.blog.views import (
    CategoryViewSet,
    CommentViewSet,
    PostViewSet,
    TagViewSet,
)

router = DefaultRouter()

router.register("categories", CategoryViewSet)
router.register("tags", TagViewSet)
router.register("posts", PostViewSet)
router.register("comments", CommentViewSet)

urlpatterns = router.urls