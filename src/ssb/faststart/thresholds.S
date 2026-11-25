.syntax unified
.thumb
.cpu cortex-m4
.text
.global fast_thresholds
fast_thresholds:
 cmp.w r9, #64
 cmp.w r9, #256
 cmp.w r0, #256
 cmp.w r0, #64
