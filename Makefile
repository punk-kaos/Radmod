PYTHON ?= python3
OEM ?= stock/RT_950Pro_V0.29_260617.BTF
OUT ?= build
.PHONY: all release dev patch test clean
all: release
release:
	$(PYTHON) build.py --oem "$(OEM)" --out "$(OUT)"
dev:
	$(PYTHON) build.py --dev --oem "$(OEM)" --out "$(OUT)/dev"
patch:
	$(PYTHON) tools/patch.py "$(OEM)" "$(OUT)/radmod.patch.json" "$(OUT)/RT950_R5_RadMod_patched.BTF"
test:
	$(PYTHON) tests/test_patcher.py
clean:
	rm -rf build
