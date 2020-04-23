# Copyright (c) 2020 fieldOfView
# StartOptimiser is released under the terms of the AGPLv3 or higher.

from UM.Extension import Extension
from cura.CuraApplication import CuraApplication
from UM.Message import Message
from UM.ConfigurationErrorMessage import ConfigurationErrorMessage

from PyQt5.QtCore import QObject
from . import LocalContainerProviderPatches

from typing import Set, TYPE_CHECKING
if TYPE_CHECKING:
    from UM.Settings.ContainerInterface import ContainerInterface

from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

class StartOptimiser(Extension, QObject,):
    def __init__(self, parent = None) -> None:
        QObject.__init__(self, parent)
        Extension.__init__(self)

        self._application = CuraApplication.getInstance()

        self.setMenuName(catalog.i18nc("@item:inmenu", "Startup Optimiser"))

        self.addMenuItem(catalog.i18nc("@item:inmenu", "Disable loading unused configuration files"), self.removeUnusedContainers)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Load only 'generic' and custom materials"), self.removeBrandedMaterials)
        self.addMenuItem("", lambda: None)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Restore all configuration files"), self.resetOptimisations)

        self._local_container_provider_patches = None
        self._application.pluginsLoaded.connect(self._onPluginsLoaded)
        self._application.getContainerRegistry().containerAdded.connect(self._onContainerAdded)

        self._application.getPreferences().addPreference("start_optimiser/container_blacklist", "")

        self._message = Message(title=catalog.i18nc("@info:title", "Startup Optimiser"))

    def _onPluginsLoaded(self) -> None:
        local_container_provider = self._application.getPluginRegistry().getPluginObject("LocalContainerProvider")
        self._local_container_provider_patches = LocalContainerProviderPatches.LocalContainerProviderPatches(local_container_provider)

        configuration_error_message = ConfigurationErrorMessage.getInstance()
        configuration_error_message.addAction("startoptimiser_clean", name = catalog.i18nc("@action:button", "Disable affected profiles"), icon = None, description = "Disable loading the corrupted configuration files but attempt to leave the rest intact.")
        configuration_error_message.actionTriggered.connect(self._configurationErrorMessageActionTriggered)

    def _onContainerAdded(self, container: "ContainerInterface") -> None:
        # make sure that this container also gets loaded the next time Cura starts
        black_list = set(self._application.getPreferences().getValue("start_optimiser/container_blacklist").split(";"))
        try:
            black_list.remove(container.id)
            self._application.getPreferences().setValue("start_optimiser/container_blacklist", ";".join(list(black_list)))
        except KeyError:
            pass

    def removeUnusedContainers(self) -> None:
        local_container_ids = self._local_container_provider_patches.getLocalContainerIds()

        active_stack_ids = set()
        active_definition_ids = set()
        active_container_ids = set()

        container_registry = self._application.getContainerRegistry()

        active_machine_stacks = set(container_registry.findContainerStacks(type = "machine"))
        active_extruder_stacks = set()
        for stack in active_machine_stacks:
            extruders = container_registry.findContainerStacks(type = "extruder_train", machine = stack.id)
            active_extruder_stacks.update(extruders)

        for stack in active_machine_stacks | active_extruder_stacks:
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
        self._addToBlackList(unused_container_ids)

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
            if not container_registry.getInstance().isReadOnly(metadata["id"]):
                # keep custom materials
                keep_branded_materials.add(metadata["base_file"])

        unused_branded_materials = branded_materials - keep_branded_materials
        self._addToBlackList(unused_branded_materials)

    def resetOptimisations(self) -> None:
        self._application.getPreferences().setValue("start_optimiser/container_blacklist", "")
        self._message.hide()
        self._message.setText(catalog.i18nc("@info:status", "Please restart Cura to restore loading all configuration files"))
        self._message.show()

    def _addToBlackList(self, container_ids:Set[str]) -> None:
        black_list = set(self._application.getPreferences().getValue("start_optimiser/container_blacklist").split(";"))
        black_list.update(container_ids)
        self._application.getPreferences().setValue("start_optimiser/container_blacklist", ";".join(list(black_list)))

        self._message.hide()
        self._message.setText(catalog.i18nc("@info:status", "On the next start of Cura %d configuration files will be skipped") % len(black_list))
        self._message.show()

    def _configurationErrorMessageActionTriggered(self, _, action_id):
        if action_id == "startoptimiser_clean":
            configuration_error_message = ConfigurationErrorMessage.getInstance()
            configuration_error_message.hide()
            self._addToBlackList(configuration_error_message._faulty_containers)
