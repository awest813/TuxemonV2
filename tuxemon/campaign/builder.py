# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Campaign build pipeline.

Implements Workflow D (Campaign Packaging and Export) from
docs/campaign_maker_mvp.md §3.2.

The builder validates a campaign directory and, if valid, packages it into
a deterministic .capsule archive (ZIP format) suitable for distribution.
"""
from __future__ import annotations

import hashlib
import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from tuxemon.campaign.validator import (
    CampaignValidator,
    ValidationReport,
)

logger = logging.getLogger(__name__)

CAPSULE_EXTENSION = ".capsule"
CAPSULE_MANIFEST_COMMENT = b"OpenCapsuleMon campaign archive"


@dataclass
class BuildResult:
    """
    Result of a campaign build operation.

    Attributes
    ----------
    success:
        True when the campaign was valid and the .capsule was written.
    output_path:
        Path to the produced .capsule file, or None on failure.
    report:
        The ValidationReport from the pre-build validation pass.
    sha256:
        Hex SHA-256 digest of the produced .capsule archive, for integrity
        verification during distribution. Empty string on failure.
    file_count:
        Number of files packaged into the archive.
    error:
        Human-readable error message when success is False.
    """

    success: bool
    output_path: Optional[Path] = None
    report: Optional[ValidationReport] = None
    sha256: str = ""
    file_count: int = 0
    error: str = ""

    def human_summary(self) -> str:
        if self.success:
            return (
                f"Build succeeded: {self.output_path} "
                f"({self.file_count} files, sha256={self.sha256[:16]}…)"
            )
        lines = [f"Build failed: {self.error}"]
        if self.report:
            for issue in self.report.blocking:
                lines.append(f"  [BLOCKING] {issue.check_id}: {issue.message}")
        return "\n".join(lines)


class CampaignBuilder:
    """
    Validates and packages a campaign directory into a .capsule archive.

    Usage::

        builder = CampaignBuilder()
        result = builder.build(Path("~/campaigns/my_campaign"))
        if result.success:
            print(f"Archive: {result.output_path}")
        else:
            print(result.human_summary())

    Parameters
    ----------
    validator:
        An optional pre-configured CampaignValidator. When None, a default
        validator is created with no monster ID whitelist.
    """

    def __init__(
        self,
        validator: Optional[CampaignValidator] = None,
    ) -> None:
        self._validator = validator or CampaignValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        campaign_dir: Path,
        output_path: Optional[Path] = None,
        *,
        dry_run: bool = False,
    ) -> BuildResult:
        """
        Validate *campaign_dir* and package it into a .capsule archive.

        Parameters
        ----------
        campaign_dir:
            Root directory of the campaign to build.
        output_path:
            Where to write the .capsule file. Defaults to
            ``<campaign_dir.parent>/<campaign_dir.name>.capsule``.
        dry_run:
            When True, run validation and compute the archive in memory but
            do not write any files. Useful for CI pre-flight checks.

        Returns
        -------
        BuildResult
            See ``BuildResult`` for field descriptions.
        """
        if not campaign_dir.exists() or not campaign_dir.is_dir():
            return BuildResult(
                success=False,
                error=f"Campaign directory does not exist: {campaign_dir}",
            )

        report = self._validator.validate(campaign_dir)

        if not report.is_valid:
            return BuildResult(
                success=False,
                report=report,
                error=(
                    f"Campaign failed validation with "
                    f"{len(report.blocking)} blocking error(s). "
                    "Fix all blocking errors before building."
                ),
            )

        if output_path is None:
            output_path = (
                campaign_dir.parent / f"{campaign_dir.name}{CAPSULE_EXTENSION}"
            )

        # Collect files in deterministic order
        file_paths = sorted(
            p for p in campaign_dir.rglob("*") if p.is_file()
        )

        # Build the archive into a buffer for hashing (avoids partial writes)
        buf = io.BytesIO()
        with zipfile.ZipFile(
            buf,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=True,
        ) as zf:
            zf.comment = CAPSULE_MANIFEST_COMMENT
            for file_path in file_paths:
                arcname = str(file_path.relative_to(campaign_dir.parent))
                zf.write(file_path, arcname=arcname)

        raw_bytes = buf.getvalue()
        digest = hashlib.sha256(raw_bytes).hexdigest()

        if not dry_run:
            output_path.write_bytes(raw_bytes)
            logger.info(
                "Campaign built: %s -> %s (%d files, sha256=%s)",
                campaign_dir.name,
                output_path,
                len(file_paths),
                digest[:16],
            )

        return BuildResult(
            success=True,
            output_path=None if dry_run else output_path,
            report=report,
            sha256=digest,
            file_count=len(file_paths),
        )

    def build_from_wizard(
        self,
        wizard,  # CampaignWizard — avoid circular import with TYPE_CHECKING
        base_dir: Path,
        output_path: Optional[Path] = None,
        *,
        dry_run: bool = False,
    ) -> BuildResult:
        """
        Generate a scaffold from *wizard* then package it.

        This convenience method combines wizard.generate_scaffold() with
        build() so creators can go from wizard → packaged archive in one call.
        """
        scaffold = wizard.generate_scaffold(base_dir)
        return self.build(scaffold.root, output_path=output_path, dry_run=dry_run)
