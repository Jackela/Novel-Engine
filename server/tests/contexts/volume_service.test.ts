/**
 * Direct contract tests for VolumeService (ADR-0005): title normalization
 * before persistence, owner-scoped delegation of placement and removal, and
 * the whole-set reorder passthrough. The fake store records every command
 * through the port type, so these tests pin service behavior — the store's
 * own invariants (last-volume refusal, merged chapters, renumbering) stay
 * with the store and its tests. Harness lives in volume_service_harness.ts.
 */
import { describe, expect, it } from "vitest";

import {
  DuplicateVolumeError,
  NotFoundError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";
import {
  CHAPTER_PAYLOAD,
  chapterDocument,
  NOW,
  PRINCIPAL,
  PROJECT_ID,
  SCOPE,
  volumeHarness,
  volumeProjection,
  volumeRecord,
} from "./volume_service_harness.js";

describe("VolumeService reads and title writes", () => {
  it("lists the project's volumes in reading order owner-scoped and clock-free", () => {
    const alpha = volumeRecord("volume-1", "Act One", 1);
    const beta = volumeRecord("volume-2", "Act Two", 2);
    const { service, lists, clockCalls } = volumeHarness({ volumes: [alpha, beta] });

    expect(service.listVolumes(PRINCIPAL, PROJECT_ID)).toEqual([
      volumeProjection(alpha),
      volumeProjection(beta),
    ]);
    expect(lists).toEqual([[SCOPE, PROJECT_ID]]);
    expect(clockCalls()).toBe(0);
  });

  it("trims the title and appends the tail volume with one clock reading", () => {
    const created = volumeRecord("volume-new", "Act Two", 2);
    const { service, adds, clockCalls } = volumeHarness({ added: created });

    expect(service.newVolume(PRINCIPAL, PROJECT_ID, { title: "  Act Two  " })).toEqual(
      volumeProjection(created),
    );
    expect(adds).toEqual([[SCOPE, PROJECT_ID, { title: "Act Two", now: NOW }]]);
    expect(clockCalls()).toBe(1);
  });

  it("refuses blank titles before persistence and without reading the clock", () => {
    const { service, adds, alters, clockCalls } = volumeHarness();
    for (const title of ["", "   ", "\t\n"]) {
      expect(() => service.newVolume(PRINCIPAL, PROJECT_ID, { title })).toThrow(
        new InvalidOperationError("Volume title is required."),
      );
      expect(() => service.retitleVolume(PRINCIPAL, PROJECT_ID, "volume-1", { title })).toThrow(
        new InvalidOperationError("Volume title is required."),
      );
    }
    expect(adds).toEqual([]);
    expect(alters).toEqual([]);
    expect(clockCalls()).toBe(0);
  });

  it("renames in place: the id passes through and the command carries no position", () => {
    const renamed = volumeRecord("volume-2", "Act Two, Revised", 2);
    const { service, alters, clockCalls } = volumeHarness({ altered: renamed });

    const payload = service.retitleVolume(PRINCIPAL, PROJECT_ID, "volume-2", {
      title: " Act Two, Revised ",
    });

    expect(alters).toEqual([
      [SCOPE, PROJECT_ID, "volume-2", { title: "Act Two, Revised", now: NOW }],
    ]);
    expect(Object.keys(alters[0]?.[3] ?? {})).toEqual(["title", "now"]);
    expect(payload).toEqual(volumeProjection(renamed));
    expect(clockCalls()).toBe(1);
  });

  it("surfaces the store's duplicate-title refusal from the append path", () => {
    const { service } = volumeHarness({ added: new DuplicateVolumeError("Act Two") });
    expect(() => service.newVolume(PRINCIPAL, PROJECT_ID, { title: "Act Two" })).toThrow(
      DuplicateVolumeError,
    );
  });
});

describe("VolumeService removal and chapter placement", () => {
  it("delegates removal whole and answers nothing", () => {
    const { service, drops } = volumeHarness();
    expect(service.removeVolume(PRINCIPAL, PROJECT_ID, "volume-2")).toBeUndefined();
    expect(drops).toEqual([[SCOPE, PROJECT_ID, "volume-2"]]);
  });

  it("surfaces the store's last-volume refusal unchanged", () => {
    const refusal = new InvalidOperationError(
      "A project must keep at least one volume; create another before deleting this one.",
    );
    const { service } = volumeHarness({ dropFailure: refusal });
    let caught: unknown;
    try {
      service.removeVolume(PRINCIPAL, PROJECT_ID, "volume-1");
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(refusal);
  });

  it("places a chapter through the store and projects the placed document", () => {
    const { service, places, clockCalls } = volumeHarness();

    const payload = service.placeChapter(PRINCIPAL, PROJECT_ID, "document-1", {
      volumeId: "volume-2",
    });

    expect(places).toEqual([[SCOPE, PROJECT_ID, "document-1", { volumeId: "volume-2", now: NOW }]]);
    expect(payload).toEqual(CHAPTER_PAYLOAD);
    expect(clockCalls()).toBe(1);
  });

  it("refuses to publish a placed document without a current revision", () => {
    const { service, places } = volumeHarness({
      placed: chapterDocument({ currentRevision: null }),
    });
    expect(() =>
      service.placeChapter(PRINCIPAL, PROJECT_ID, "document-1", { volumeId: "volume-2" }),
    ).toThrow(new InvalidOperationError("Document has no current revision."));
    // The refusal is the projection contract: the store command was issued.
    expect(places).toHaveLength(1);
  });

  it("surfaces the store's non-chapter refusal unchanged", () => {
    const refusal = new InvalidOperationError("Only chapters belong to volumes.");
    const { service, places } = volumeHarness({ placed: refusal });
    let caught: unknown;
    try {
      service.placeChapter(PRINCIPAL, PROJECT_ID, "outline-1", { volumeId: "volume-2" });
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(refusal);
    expect(places).toHaveLength(1);
  });

  it("propagates a not-found target volume from the store", () => {
    const { service } = volumeHarness({ placed: new NotFoundError("Volume not found: ghost.") });
    expect(() =>
      service.placeChapter(PRINCIPAL, PROJECT_ID, "document-1", { volumeId: "ghost" }),
    ).toThrow(new NotFoundError("Volume not found: ghost."));
  });
});

describe("VolumeService whole-set reorder", () => {
  it("forwards the client's exact order and returns the renumbered sequence", () => {
    const order = ["volume-3", "volume-1", "volume-2"];
    const { service, renumbers, clockCalls } = volumeHarness();

    const payloads = service.applyVolumeOrder(PRINCIPAL, PROJECT_ID, order);

    expect(renumbers).toEqual([[SCOPE, PROJECT_ID, order, NOW]]);
    expect(payloads.map((volume) => volume.id)).toEqual(order);
    expect(payloads.map((volume) => volume.position)).toEqual([1, 2, 3]);
    expect(clockCalls()).toBe(1);
  });

  it("surfaces the store's whole-set refusal and answers nothing", () => {
    const refusal = new InvalidOperationError("Reorder must include every project volume once.");
    const { service } = volumeHarness({ renumbered: refusal });
    let caught: unknown;
    try {
      service.applyVolumeOrder(PRINCIPAL, PROJECT_ID, ["volume-1"]);
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(refusal);
  });
});
