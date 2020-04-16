# Copyright (c) 2020 fieldOfView
# StartOptimiser is released under the terms of the AGPLv3 or higher.

from UM.Extension import Extension
from cura.CuraApplication import CuraApplication

from PyQt5.QtCore import QObject

from . import LocalContainerProviderPatches

from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

class StartOptimiser(Extension, QObject,):
    def __init__(self, parent = None) -> None:
        QObject.__init__(self, parent)
        Extension.__init__(self)

        self._application = CuraApplication.getInstance()

        self.setMenuName(catalog.i18nc("@item:inmenu", "Startup Optimiser"))
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Disable loading unused configuration files"), self.optimiseStartup)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Load only 'generic' materials"), self.removeBrandedMaterials)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Restore all configuration files"), self.resetOptimisations)

        self._local_container_provider_patches = None

        self._application.pluginsLoaded.connect(self._onPluginsLoaded)

        self._application.getPreferences().addPreference("start_optimiser/id_blacklist", "")

    def _onPluginsLoaded(self) -> None:
        local_container_provider = self._application.getPluginRegistry().getPluginObject("LocalContainerProvider")
        self._local_container_provider_patches = LocalContainerProviderPatches.LocalContainerProviderPatches(local_container_provider)

    def optimiseStartup(self) -> None:
        local_container_ids = self._local_container_provider_patches.getLocalContainerIds()

        active_stack_ids = set()
        active_definition_ids = set()
        active_container_ids = set()

        container_registry = self._application.getContainerRegistry()
        container_stacks = container_registry.findContainerStacks()

        for stack in container_stacks:
            if stack.getMetaDataEntry("type") not in ["machine", "extruder_train"]:
                continue
            active_stack_ids.add(stack.id)
            active_definition_ids.add(stack.definition.id)

            # add inherited definitions
            active_definition_ids.update(
                [self._local_container_provider_patches._pathToId(p) for p in stack.definition.getInheritedFiles()]
            )

            # add quality_definition
            quality_definition_id = stack.getMetaDataEntry("quality_definition", "")
            if quality_definition_id:
                active_definition_ids.add(quality_definition_id)

        for definition_id in active_definition_ids:
            instance_containers_metadata = container_registry.findInstanceContainersMetadata(definition=definition_id)
            for metadata in instance_containers_metadata:
                container_id = metadata["id"]
                if metadata["type"] == "material":
                    container_id = metadata["base_file"]
                active_container_ids.add(container_id)

        unused_container_ids = local_container_ids - (active_stack_ids | active_definition_ids | active_container_ids)
        self._application.getPreferences().setValue("start_optimiser/id_blacklist", ";".join(list(unused_container_ids)))

    def removeBrandedMaterials(self) -> None:
        branded_materials = set()
        keep_branded_materials = set()

        container_registry = self._application.getContainerRegistry()
        container_stacks = container_registry.findContainerStacks()

        for stack in container_stacks:
            if stack.getMetaDataEntry("type") not in ["machine", "extruder_train"]:
                continue

            if stack.material.getMetaDataEntry("brand", default="generic").lower() != "generic":
                keep_branded_materials.add(stack.material.getMetaDataEntry("base_file"))

        materials_metadata = container_registry.findInstanceContainersMetadata(type="material")
        for metadata in materials_metadata:
            if "brand" not in metadata or metadata["brand"].lower() != "generic":
                branded_materials.add(metadata["base_file"])

        unused_branded_materials = branded_materials - keep_branded_materials
        self._application.getPreferences().setValue("start_optimiser/id_blacklist", ";".join(list(unused_branded_materials)))

    def resetOptimisations(self) -> None:
        self._application.getPreferences().setValue("start_optimiser/id_blacklist", "")
