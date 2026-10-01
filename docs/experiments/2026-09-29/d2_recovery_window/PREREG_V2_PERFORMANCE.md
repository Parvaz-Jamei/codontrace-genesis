# D-2 preregistration, version 2 — resource transfer

**Date:** 2026-10-02. This file does not revise `design.md` and it does not
confirm `FI-RARECLASS-CONTACT-YIELD-V1`.

## What the old record already showed

The locked rule was mean rare-class contact yield at least **1.25×** the
run's own baseline for at least **3 consecutive** boundaries. The positive
control did not reach it. That is a measurement barrier. Zeros on the arms
do not reject an intervention effect. `analysis.json` and the raw histories
stay as that record.

Two seeds at three checkpoints were stored as six histories. They are two
histories. Checkpoints inside one seed are nested.

Pairing nodes by sorted name is not an engine contact.
`topology_identified` and `contact_identified` stay false for that pairing.

## New endpoint, registered before any new claim

| Field | Value |
|---|---|
| ID | `FI-RESOURCE-TRANSFER-V2` |
| Observable | ATP paid on a contact that names `source_id`, `recipient_id` and `contact_id` |
| Positive control | one predefined instrument transfer of a known positive amount |
| Negative control | predefined edge removal, same cost, different contact id, paid transfer 0 |
| Not this endpoint | genome-digest return, and population survival |

The positive control is an instrument check. Reaching it is not a discovery
and it is not evidence for the 1.25× rule.

## Replicate unit

`n` is the number of seeds. A checkpoint is not an independent replicate.
