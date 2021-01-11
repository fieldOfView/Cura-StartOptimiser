from UM.Application import Application
from UM.Logger import Logger
from UM.MimeTypeDatabase import MimeType, MimeTypeDatabase
from UM.Settings.ContainerRegistry import ContainerRegistry

import urllib
import os.path

from typing import Set, Optional, Tuple


class LocalContainerProviderPatches():
    def __init__(self, local_container_provider) -> None:
        self._local_container_provider = local_container_provider
        if hasattr(self._local_container_provider, "_pathToIdAndMime"):
            self._local_container_provider._pathToIdAndMime = self._pathToIdAndMime
        else:
            self._local_container_provider._pathToId = self._pathToId

        self._local_container_ids = set()  # type: Set[str]
        self._id_blacklist = Application.getInstance().getPreferences().getValue("start_optimiser/container_blacklist").split(";")

    def getLocalContainerIds(self) -> Set[str]:
        return self._local_container_ids

    def _pathToId(self, path: str) -> Optional[str]:
        """Converts a file path to the ID of the container it represents."""
        result = None
        mime = self._local_container_provider._pathToMime(path)
        if mime:
            result = urllib.parse.unquote_plus(mime.stripExtension(os.path.basename(path)))

            # START PATCH
            self._local_container_ids.add(result)
            if result in self._id_blacklist:
                result = None
            # END PATCH
        return result

    def _pathToIdAndMime(self, path: str) -> Tuple[Optional[str], Optional[MimeType]]:
        """ Faster combination of _pathToMime and _pathToID
            When we want to know the mime and the ID, it's better to use this function, as this prevents an extra
            mime detection from having to be made.
        """
        try:
            mime = MimeTypeDatabase.getMimeTypeForFile(path)
        except MimeTypeDatabase.MimeTypeNotFoundError:
            Logger.log("w", "MIME type could not be found for file: {path}, ignoring it.".format(path = path))
            return None, None
        if mime.name not in ContainerRegistry.mime_type_map:  # The MIME type is known, but it's not a container.
            return None, None
        recovered_id = None
        if mime:
            recovered_id = urllib.parse.unquote_plus(mime.stripExtension(os.path.basename(path)))

            # START PATCH
            self._local_container_ids.add(recovered_id)
            if recovered_id in self._id_blacklist:
                return None, None
            # END PATCH
        return recovered_id, mime
