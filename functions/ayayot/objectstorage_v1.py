"""
API that authorizes access to objects in object storage
"""
from ixoncdkingress.function.context import FunctionContext, FunctionResource
from ixoncdkingress.function.objectstorage.types import ResourceType, PathMapping, PathResponse, \
    ListPathResponse, PathData


def _has_access_to_files_of_resource(
        company: FunctionResource,
        resource: FunctionResource,
    ) -> bool:
    """
    Validates if the caller is authorized to access files for the given
    resource.
    """
    assert resource.permissions is not None  # type hint
    assert company.permissions is not None  # type hint
    if (
            'MANAGE_AGENT' not in resource.permissions and
            'COMPANY_ADMIN' not in company.permissions
        ):
        return False

    return True

def _format_path_for_resource(resource: FunctionResource, typ: ResourceType) -> str:
    """
    Formats the path at which files for the given resource are stored
    """
    root = 'assets'

    if typ != ResourceType.ASSET:
        root = 'agents'

    return f'{root}/{resource.public_id}/'

def _create_single_response(
        resource: FunctionResource, typ: ResourceType,
    ) -> PathResponse:
    """
    Creates a single-path response, as is
    used by authorize_upload, authorize_download & authorize_delete
    """
    return PathResponse(
        result='success',
        data=PathData(
            path=_format_path_for_resource(resource, typ),
        ),
    )

def _create_mapping_for_resource(res: tuple[FunctionResource, ResourceType]):
    resource, typ = res
    return PathMapping(
        publicId=resource.public_id,
        type=typ,
        path=_format_path_for_resource(resource, typ)
    )

def _create_multi_response(
        resources: list[tuple[FunctionResource, ResourceType]]
    ) -> ListPathResponse:
    """
    Creates a multi-path response, as is used by authorize_list
    """
    mappings = map(_create_mapping_for_resource, resources)

    return ListPathResponse(
        result='success',
        data=list(mappings),
    )


def _add_asset_descendant_resources(
    context: FunctionContext,
    resources: list[tuple[FunctionResource, ResourceType]],
) -> None:
    """
    Adds all resources that are descendants of the given asset to the given resources list
    """
    for resource, r_type in resources:
        if r_type == ResourceType.ASSET:
            result = context.api_client.get(
                "AssetDescendantList",
                {"publicId": resource.public_id, "fields": "publicId,name"},
            )["data"]
            resources.extend(
                [
                    (
                        FunctionResource(
                            public_id=res["publicId"],
                            name=res["name"],
                            custom_properties={},
                            permissions=set(),
                        ),
                        ResourceType.ASSET,
                    )
                    for res in result
                ]
            )


def _request_for(context: FunctionContext) -> tuple[FunctionResource, ResourceType] | None:
    """
    Detects the target resource of the request, preferring assets to agents.
    Will also return the type of the resource.
    """
    # A company is required in all cases
    if not context.company:
        return None

    target = context.agent
    typ = ResourceType.AGENT

    if context.asset:
        target = context.asset
        typ = ResourceType.ASSET

    if not target:
        return None

    return target, typ

def _authorize_single(context: FunctionContext, check_has_manage: bool) -> PathResponse | None:
    if (target_typ := _request_for(context)) is None:
        return None

    target, typ = target_typ

    assert context.company  # type check

    if check_has_manage and not _has_access_to_files_of_resource(
            context.company,
            target,
        ):
        return None

    return _create_single_response(target, typ)

@FunctionContext.expose
def authorize_upload(context: FunctionContext) -> PathResponse | None:
    """
    Method to validate if and where the caller is allowed
    to upload a blob to the object storage.
    """
    return _authorize_single(context, True)

@FunctionContext.expose
def authorize_list(
        context: FunctionContext
    ) -> ListPathResponse | None:
    """
    Method to validate if and where the caller is allowed
    to get the blob list from the object storage.
    """
    if (target_typ := _request_for(context)) is None:
        return None

    target, typ = target_typ

    resources = [(target, typ)]

    # If the target was an asset with a linked agent,
    # we should also return a path mapping for that agent
    if typ == ResourceType.ASSET and context.agent is not None:
        resources.append((context.agent, ResourceType.AGENT))

    _add_asset_descendant_resources(context, resources)

    return _create_multi_response(resources)

@FunctionContext.expose
def authorize_download(context: FunctionContext) -> PathResponse | None:
    """
    Method to validate if and where the caller is allowed
    to download a blob from the object storage.
    """
    return _authorize_single(context, False)

@FunctionContext.expose
def authorize_delete(context: FunctionContext) -> PathResponse | None:
    """
    Method to validate if and where the caller is allowed
    to delete a blob from the object storage.
    """
    return _authorize_single(context, True)
