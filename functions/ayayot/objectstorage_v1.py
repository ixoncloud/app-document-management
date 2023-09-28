"""
Reserve API to handle access checks for the object storage.
"""

from typing import Dict

from ixoncdkingress.cbc.context import CbcContext

def _validate_agent_access(
        context: CbcContext,
        check_has_manage_agent: bool = True,
    ) -> Dict[str, str | Dict[str, str]] | None:
    """
    Validates if the Cloud function is being called scoped to an agent and
    optionally validates if the caller has MANAGE_AGENT permissions.

    Returns None if the caller shouldn't have access else returns the path
    to the blob.
    """
    if not context.agent:
        return None

    assert context.agent.permissions # type hint
    if check_has_manage_agent and 'MANAGE_AGENT' not in context.agent.permissions:
        return None

    return {
        'result': 'success',
        'data': {
            'path': f'agents/{context.agent.public_id}/',
        }
    }

@CbcContext.expose
def authorize_upload(context: CbcContext):
    """
    Method to validate if and where the caller is allowed
    to upload a blob to the object storage.
    """
    return _validate_agent_access(context)

@CbcContext.expose
def authorize_list(context: CbcContext):
    """
    Method to validate if and where the caller is allowed
    to get the blob list from the object storage.
    """
    return _validate_agent_access(context, False)

@CbcContext.expose
def authorize_download(context: CbcContext):
    """
    Method to validate if and where the caller is allowed
    to download a blob from the object storage.
    """
    return _validate_agent_access(context, False)

@CbcContext.expose
def authorize_delete(context: CbcContext):
    """
    Method to validate if and where the caller is allowed
    to delete a blob from the object storage.
    """
    return _validate_agent_access(context)
