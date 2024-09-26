import smartparking.service.data as ps
from smartparking.api.commons import (
    APIRouter,
    Authorized,
    Depends,
    Errors,
    Query,
    Request,
    URLFor,
    abort_with,
    c,
    errorModel,
    vq,
    vr,
    with_user,
)
from smartparking.api.shared.schema import SelfContainedGenerateSchema

router = APIRouter()

#
# @router.post(
#     "/images",
#     status_code=201,
#     openapi_extra={
#         "requestBody": {
#             "content": {
#                 "multipart/form-data": {
#                     "schema": vq.CreateResumeBody.model_json_schema(
#                         schema_generator=SelfContaindGenerateSchema
#                     ),
#                     "encoding": {
#                         "photo": {
#                             "contentType": ["image/png", "image/jpeg"],
#                         },
#                     },
#                 },
#             },
#         },
#     },
#     responses={
#         201: {"description": ""},
#     },
# )
