# =============================================================================
# MPIQ Library Makefile
# =============================================================================
# Usage:
#   make          - Build all targets (library + test cases + server daemons)
#   make clean    - Remove all generated binaries and object files
#
# Configuration (adjust for your environment):
#   PY_DIR  - Directory containing Python header files (Python.h)
#   PY_LIB  - Directory containing Python shared library (libpython3.x.so)
#   LDPYLIBS- Link against the correct Python version (e.g. -lpython3.11)
# =============================================================================
LIB_SRC_DIR   = MPIQ
TEST_SRC_DIR  = test
SERVER_SRC_DIR= server
LIB_DIR       = libs
PY_DIR        = /usr/include/python3.11    # Python 3.11 header directory
PY_LIB        = /usr/lib/x86_64-linux-gnu  # Python shared library directory

CC            = mpicc                  # Use MPI C compiler wrapper
CFLAGS        = -g -Wall               # Enable debug symbols and all warnings
LDFLAGS       = -L$(LIB_DIR)          # Link against the local libs directory
FINDLIB       = -I$(PY_DIR)           # Include Python headers
LDPY          = -L$(PY_LIB)           # Python library search path
LDLIBS        = -lMPIQ                 # Link against the MPIQ static library
LDPYLIBS      = -lpython3.11           # Link against Python 3.11 runtime
AR            = ar                     # Archiver for creating static library
ARFLAGS       = rcs                    # ar flags: replace, create, use index
RM            = rm -rf                 # Remove command

# Source and object file lists for the MPIQ library
MPIQ_LIB_SRC = $(wildcard $(LIB_SRC_DIR)/*.c)
MPIQ_OBJECTS = $(MPIQ_LIB_SRC:$(LIB_SRC_DIR)/%.c=$(LIB_DIR)/%.o)
MPIQ_LIB     = $(LIB_DIR)/libMPIQ.a

# All binary targets to build
TARGETS = \
    $(SERVER_SRC_DIR)/server_barrier1 \
    $(SERVER_SRC_DIR)/server_barrier2 \
    $(SERVER_SRC_DIR)/server_card \
    $(TEST_SRC_DIR)/test1_sendrecv \
    $(TEST_SRC_DIR)/test2_bcast \
    $(TEST_SRC_DIR)/test6_barrier \
    $(SERVER_SRC_DIR)/server_user \
    $(TEST_SRC_DIR)/test3_scatter \
    $(TEST_SRC_DIR)/test4_gather \
    $(TEST_SRC_DIR)/test5_allgather \

all: $(TARGETS)

# Create libs directory if it does not exist
$(LIB_DIR):
	mkdir -p $@

# Compile each MPIQ library source file to an object file
# -MD -MP generates dependency files for incremental builds
$(LIB_DIR)/%.o: $(LIB_SRC_DIR)/%.c | $(LIB_DIR)
	@$(CC) $(CFLAGS) -c -o $@ $< -MD -MP 

# Archive all object files into a static library
$(MPIQ_LIB): $(MPIQ_OBJECTS)
	@$(AR) $(ARFLAGS) $@ $^

# Build test programs: link against MPIQ library and Python runtime
# -O2: optimization; -fopenmp: OpenMP support; -lm: math library
$(TEST_SRC_DIR)/%: $(TEST_SRC_DIR)/%.c $(MPIQ_LIB)
	@$(CC) $(CFLAGS) $(LDFLAGS) $(FINDLIB) $(LDPY) -o $@ $< $(LDLIBS) $(LDPYLIBS) -Wall -O2 -fopenmp -lm

# Build server daemon programs (no OpenMP or math library needed)
$(SERVER_SRC_DIR)/%: $(SERVER_SRC_DIR)/%.c $(MPIQ_LIB)
	@$(CC) $(CFLAGS) $(LDFLAGS) $(FINDLIB) $(LDPY) -o $@ $< $(LDLIBS) $(LDPYLIBS)

# Include auto-generated dependency files for incremental rebuild support
-include $(MPIQ_OBJECTS:.o=.d)

# Clean all generated binaries and intermediate files
clean:
	@$(RM) $(LIB_DIR)/*.o $(LIB_DIR)/*.d $(LIB_DIR)/*.a $(TARGETS) 

