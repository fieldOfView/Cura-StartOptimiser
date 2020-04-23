from UM.Application import Application

import urllib
import os.path

from typing import Set, Optional

class LocalContainerProviderPatches():
    def __init__(self, local_container_provider) -> None:
        self._local_container_provider = local_container_provider
        self._local_container_provider._pathToId = self._pathToId

        self._local_container_ids = set()
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
