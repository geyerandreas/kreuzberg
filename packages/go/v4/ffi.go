package kreuzberg

/*
#cgo !windows pkg-config: kreuzberg-ffi
#cgo !pkg-config CFLAGS: -I${SRCDIR}/internal/ffi
#cgo !pkg-config,!windows LDFLAGS: -lkreuzberg_ffi

#include "internal/ffi/kreuzberg.h"
#include <stdlib.h>
#include <stdint.h>
*/
import "C"
