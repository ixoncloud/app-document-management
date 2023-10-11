"""
API that authorizes access to objects in object storage
"""

from typing import Dict

from ixoncdkingress.cbc.context import CbcContext, CbcResource


def _has_access_to_files(
        context: CbcContext,
        check_has_manage: bool,
    ) -> bool:
    """
    Validates if the caller is authorized to access files for the resource
    on which the backend component call was made. Only assets & agents are
    supported
    """
    resource = context.agent
    if context.asset:
        resource = context.asset

    # Needs to be called for an asset or agent
    if not resource:
        return False

    assert resource.permissions is not None # type hint
    if check_has_manage and (
            'MANAGE_AGENT' not in resource.permissions and
            'COMPANY_ADMIN' not in context.company.permissions
        ):
        return False

    return True

def _create_single_response(
        resource: CbcResource, is_asset: bool
    ) -> Dict[str, str | Dict[str, str]]:

    root = 'assets'

    if not is_asset:
        root = 'agents'

    return {
        'result': 'success',
        'data': {
            'path': f'{root}/{resource.public_id}/',
        }
    }

@CbcContext.expose
def authorize_upload(context: CbcContext):
    """
    Method to validate if and where the caller is allowed
    to upload a blob to the object storage.
    """
    if not _has_access_to_files(context, check_has_manage=True):
        return None

    return _create_single_response(context.agent_or_asset, context.asset is not None)

@CbcContext.expose
def authorize_list(context: CbcContext):
    """
    Method to validate if and where the caller is allowed
    to get the blob list from the object storage.
    """
    if not _has_access_to_files(context, check_has_manage=False):
        return None

    return _create_single_response(context.agent_or_asset, context.asset is not None)

@CbcContext.expose
def authorize_download(context: CbcContext):
    """
    Method to validate if and where the caller is allowed
    to download a blob from the object storage.
    """
    if not _has_access_to_files(context, check_has_manage=False):
        return None

    return _create_single_response(context.agent_or_asset, context.asset is not None)

@CbcContext.expose
def authorize_delete(context: CbcContext):
    """
    Method to validate if and where the caller is allowed
    to delete a blob from the object storage.
    """
    if not _has_access_to_files(context, check_has_manage=True):
        return None

    return _create_single_response(context.agent_or_asset, context.asset is not None)
