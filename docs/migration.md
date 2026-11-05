# Moving to ETA Heating

[Deutsche Version](migration.de.md)

This guide is for installations that still use the previous repository, `Tidone/homeassistant_eta_integration`. Version 1.4.3 of that repository saves the setup automatically, so ETA Heating can restore it without a new scan.

The previous version keeps working, but it no longer receives updates. You can switch at any time.

## What is kept

- Selected entities and settings
- Entity IDs and device IDs
- Names, areas, labels and disabled or hidden states
- History

## Before you start

1. Create a Home Assistant backup.
2. Update the previous integration to **1.4.3**.
3. Restart Home Assistant once. This saves the setup to `.storage/eta_webservices.migration`.

Only version 1.4.3 saves your setup. If you switch directly from 1.4.2 or older, nothing is saved, and you have to set up ETA Heating from scratch, including the scan and your selection.

## Home Assistant 2026.11 and newer

The Marketplace does not allow two installed repositories with the same domain, so the previous integration has to be removed first.

1. Go to **Settings → Marketplace** and open the installed **ETA** integration.
2. Open the three dots menu, select **Uninstall** and confirm **Delete and uninstall**.
3. In the Marketplace overview, open the three dots menu, select **Custom repositories** and remove the previous repository.
4. Search for **ETA Heating**, select **Install** and restart Home Assistant.
5. Go to **Settings → Devices & services → Add Integration** and search for **ETA Heating**.
6. Select **Restore previous setup**.

## Home Assistant 2026.10 and older

1. Go to **Settings → Devices & services**, open the ETA integration and delete it.
2. In **HACS**, uninstall the previous integration and remove its custom repository.
3. Search for **ETA Heating** in HACS, select **Download** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add Integration** and search for **ETA Heating**.
5. Select **Restore previous setup**.

## After the switch

The entry is migrated automatically and the saved setup is deleted. Check that the entities show values and that your automations and dashboards work as before.

A repair notice about the entity naming scheme can appear after the restore. It is informational, and no action is needed.

## Troubleshooting

**Restore previous setup is not offered.** The setup was not saved, or the same address is already configured. Check that version 1.4.3 was running and that Home Assistant was restarted before the switch.

**The Marketplace reports that the directory belongs to another repository.** The previous integration is still installed. Complete steps 1 to 3 for your Home Assistant version.
