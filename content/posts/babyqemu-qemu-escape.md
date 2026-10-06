---
title: "babyqemu — A QEMU Escape Writeup"
date: 2026-10-06
draft: false
summary: "Walking through a QEMU VM-escape challenge end to end: from an emulated PCI device to code execution on the host."
description: "A QEMU escape writeup on the HITB GSEC 2017 babyqemu challenge — PCI/MMIO recon, an OOB write in a custom device, and a function-pointer overwrite into system()."
tags: ["vm-escape", "qemu", "virtualization", "pwn", "hitb", "exploitation"]
categories: ["writeups"]
ShowToc: true
TocOpen: false
weight: 1
# cover:
#   image: "images/babyqemu-cover.png"   # optional: drop a cover in assets or static/
#   alt: "babyqemu"
#   caption: ""
#   relative: false
---

> Writeup of the HITB GSEC 2017 **babyqemu** challenge — my first deep dive into
> virtualization exploitation. Reference I worked from:
> https://kitctf.de/writeups/hitb2017/babyqemu
>
> _Remove this blockquote before publishing._

<!--
AUTHORING NOTES (delete as you go):
  - Each section below is one of the six you planned. Fill the prose, drop code
    into the fenced blocks, and put screenshots/diagrams in  assets/  (page
    bundle) or  static/images/  and reference them.
  - Grep for  TODO  to see what's left:   grep -rn TODO content/
  - Code blocks: ```c / ```python / ```bash / ```gdb  — copy button + line
    numbers are already on site-wide.
  - Keep the reader model in mind: someone who knows userland pwn (stack
    overflows, ROP, ASLR) but has never looked at a hypervisor.
-->

## Introduction — what a VM escape is

<!-- TODO: 2–4 short paragraphs. Frame it for a userland-pwn reader:
     - the guest/host trust boundary and why crossing it matters
     - where the attack surface lives (device emulation)
     - one sentence on what this challenge ends in (host code exec) -->

## Challenge setup

<!-- TODO: how the target is packaged and how you run it. -->

```bash
# TODO: the launch command / run script (qemu invocation, flags)
```

<!-- TODO: note kernel/initramfs, how you get a guest shell, how files move
     guest<->host, and your debugging setup (attaching to the qemu process). -->

```bash
# TODO: debugging setup — attach gdb to the qemu-system process, etc.
```

## Recon — the emulated PCI device

<!-- TODO: enumerating the custom device from inside the guest. -->

```bash
# TODO: lspci / sysfs enumeration, BAR layout
```

<!-- TODO: map out the device:
     - its BARs and which is MMIO vs PMIO
     - the MMIO read/write handlers and the registers they expose
     - a small table or diagram of the register map (put a figure in assets/) -->

![device register map](TODO-replace-or-delete.png)

## Vulnerability analysis — the OOB write

<!-- TODO: walk the device's read/write handlers and show where bounds are
     missing. Paste only the minimal relevant struct / handler excerpt. -->

```c
// TODO: the vulnerable handler / struct (minimal excerpt)
```

<!-- TODO: state the primitive precisely:
     - what you control (offset, value, width)
     - what you can reach relative to the allocation
     - why the check is insufficient -->

## Exploitation — function pointer → system()

<!-- TODO: from primitive to host code execution, in order. -->

```c
// TODO: the exploit (guest-side program driving the MMIO writes)
```

<!-- TODO: narrate the chain:
     - what you overwrite and why that pointer
     - how you stage the argument for system()
     - the trigger, then the pop -->

```text
TODO: paste the final run — the moment the host command executes.
```

## The bigger picture — real-world VM-escape attack surface

<!-- TODO: zoom out from the toy device to production reality.
     - device emulation as the dominant hypervisor attack surface
     - a few real CVE classes/examples in QEMU/KVM device models
     - how hardening (seccomp sandbox, vhost-user, rust-vmm/virtio) changes it
     - what you'd look at next -->

---

<!-- Optional closing: references and tooling you used. Keep links; keep it short. -->

### References

- HITB GSEC 2017 babyqemu — reference writeup: https://kitctf.de/writeups/hitb2017/babyqemu
- TODO: anything else you leaned on
