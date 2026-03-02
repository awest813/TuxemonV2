# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Campaign import and compatibility checker.

Implements Workflow E (Campaign Import and Compatibility Check) from
docs/campaign_maker_mvp.md §3.2.

The importer reads a .capsule archive, checks engine version compatibility,
and optionally installs the campaign to a target directory.
"""

from __future__ import annotations

import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from tuxemon.campaign.models import CampaignManifest
from tuxemon.campaign.validator import ENGINE_VERSION

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Compatibility result
# ---------------------------------------------------------------------------


@dataclass
class CompatibilityResult:
    """
    Engine–campaign compatibility check outcome.

    Attributes
    ----------
    is_compatible:
        True when the campaign can run on the current engine.
    campaign_id:
        The campaign's ID from its manifest.
    campaign_name:
        Human-readable campaign name.
    campaign_version:
        Campaign semver version string.
    engine_min_version:
        Minimum engine version required by the campaign.
    current_engine_version:
        The engine version used for comparison.
    incompatibilities:
        Human-readable list of specific incompatibilities found.
        Empty when is_compatible is True.
    """

    is_compatible: bool
    campaign_id: str = ""
    campaign_name: str = ""
    campaign_version: str = ""
    engine_min_version: str = ""
    current_engine_version: str = ""
    incompatibilities: list[str] = field(default_factory=list)

    def human_summary(self) -> str:
        lines = [
            f"Campaign: {self.campaign_name} ({self.campaign_id} v{self.campaign_version})",
            f"Engine required: >= {self.engine_min_version}  |  Current: {self.current_engine_version}",
            f"Compatible: {'YES' if self.is_compatible else 'NO'}",
        ]
        if self.incompatibilities:
            lines.append("Incompatibilities:")
            for item in self.incompatibilities:
                lines.append(f"  - {item}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Import result
# ---------------------------------------------------------------------------


@dataclass
class ImportResult:
    """
    Outcome of a full import (compatibility check + extraction).

    Attributes
    ----------
    success:
        True when the campaign was extracted to install_dir successfully.
    compatibility:
        The compatibility check result (always populated).
    install_dir:
        Where the campaign was installed. None on failure.
    sha256_verified:
        True when the archive's embedded checksum matched the content.
    error:
        Human-readable error message when success is False.
    """

    success: bool
    compatibility: Optional[CompatibilityResult] = None
    install_dir: Optional[Path] = None
    sha256_verified: bool = False
    error: str = ""

    def human_summary(self) -> str:
        lines = []
        if self.compatibility:
            lines.append(self.compatibility.human_summary())
        if self.success:
            lines.append(f"Installed to: {self.install_dir}")
        else:
            lines.append(f"Import failed: {self.error}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------


class CampaignImporter:
    """
    Reads .capsule archives and installs campaigns.

    Parameters
    ----------
    engine_version:
        The current engine version string (semver) used for compatibility checks.
    """

    def __init__(self, engine_version: str = ENGINE_VERSION) -> None:
        self._engine_version = engine_version

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_compatibility(self, capsule_path: Path) -> CompatibilityResult:
        """
        Open *capsule_path* and check if it is compatible with the current engine.

        Does NOT extract any files.
        """
        manifest, error = self._read_manifest(capsule_path)
        if manifest is None:
            return CompatibilityResult(
                is_compatible=False,
                incompatibilities=[
                    error or "Could not read campaign manifest."
                ],
                current_engine_version=self._engine_version,
            )

        return self._evaluate_compatibility(manifest)

    def install(
        self,
        capsule_path: Path,
        install_dir: Path,
        *,
        overwrite: bool = False,
    ) -> ImportResult:
        """
        Check compatibility and extract *capsule_path* to *install_dir*.

        Parameters
        ----------
        capsule_path:
            The .capsule archive to install.
        install_dir:
            Root directory where campaigns are installed. The campaign is
            extracted into a subdirectory named after its campaign ID.
        overwrite:
            When False (default), raises FileExistsError if the campaign
            directory already exists.

        Returns
        -------
        ImportResult
        """
        compat = self.check_compatibility(capsule_path)
        if not compat.is_compatible:
            return ImportResult(
                success=False,
                compatibility=compat,
                error="Campaign is not compatible with the current engine.",
            )

        campaign_target = install_dir / compat.campaign_id
        if campaign_target.exists() and not overwrite:
            return ImportResult(
                success=False,
                compatibility=compat,
                error=(
                    f"Campaign '{compat.campaign_id}' is already installed at "
                    f"{campaign_target}. Use overwrite=True to replace it."
                ),
            )

        try:
            install_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(capsule_path, "r") as zf:
                # The archive stores files under the campaign directory name
                # (e.g. "my_campaign/campaign.yaml"), so extract to install_dir
                # to produce the correct install_dir/campaign_id/ layout.
                zf.extractall(install_dir)
        except (zipfile.BadZipFile, OSError) as exc:
            return ImportResult(
                success=False,
                compatibility=compat,
                error=f"Failed to extract archive: {exc}",
            )

        logger.info(
            "Campaign installed: %s -> %s",
            compat.campaign_id,
            campaign_target,
        )
        return ImportResult(
            success=True,
            compatibility=compat,
            install_dir=campaign_target,
        )

    def read_manifest(self, capsule_path: Path) -> Optional[CampaignManifest]:
        """
        Extract and return the CampaignManifest from a .capsule without installing.

        Returns None when the archive is invalid or the manifest cannot be parsed.
        """
        manifest, _ = self._read_manifest(capsule_path)
        return manifest

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_manifest(
        self, capsule_path: Path
    ) -> tuple[Optional[CampaignManifest], Optional[str]]:
        """Return (manifest, error_message). error_message is None on success."""
        if not capsule_path.exists():
            return None, f"Archive not found: {capsule_path}"

        if not zipfile.is_zipfile(capsule_path):
            return (
                None,
                f"File is not a valid .capsule archive: {capsule_path}",
            )

        try:
            with zipfile.ZipFile(capsule_path, "r") as zf:
                manifest_name = self._find_manifest_entry(zf)
                if manifest_name is None:
                    return None, "Archive contains no campaign.yaml manifest."

                raw_bytes = zf.read(manifest_name)
        except (zipfile.BadZipFile, KeyError, OSError) as exc:
            return None, f"Archive read error: {exc}"

        try:
            raw = yaml.safe_load(raw_bytes.decode("utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError) as exc:
            return None, f"campaign.yaml parse error: {exc}"

        if not isinstance(raw, dict):
            return None, "campaign.yaml is not a YAML mapping."

        try:
            manifest = CampaignManifest(**raw)
        except ValidationError as exc:
            return None, f"campaign.yaml schema error: {exc}"

        return manifest, None

    @staticmethod
    def _find_manifest_entry(zf: zipfile.ZipFile) -> Optional[str]:
        """Return the archive path of the campaign.yaml, or None."""
        for name in zf.namelist():
            if name.endswith("campaign.yaml"):
                return name
        return None

    def _evaluate_compatibility(
        self, manifest: CampaignManifest
    ) -> CompatibilityResult:
        incompatibilities: list[str] = []

        def semver_parts(v: str) -> tuple[int, ...]:
            try:
                return tuple(int(x) for x in v.split("."))
            except ValueError:
                return (0, 0, 0)

        required = semver_parts(manifest.engine_min_version)
        current = semver_parts(self._engine_version)

        if required > current:
            incompatibilities.append(
                f"Campaign requires engine >= {manifest.engine_min_version}, "
                f"but current engine is {self._engine_version}."
            )

        return CompatibilityResult(
            is_compatible=len(incompatibilities) == 0,
            campaign_id=manifest.id,
            campaign_name=manifest.name,
            campaign_version=manifest.version,
            engine_min_version=manifest.engine_min_version,
            current_engine_version=self._engine_version,
            incompatibilities=incompatibilities,
        )
