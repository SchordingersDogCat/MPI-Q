import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit.compiler import schedule
from qiskit.pulse import Play, Waveform, DriveChannel
from qiskit.exceptions import QiskitError
# Import backend specifically designed for pulses
from qiskit.providers.fake_provider import FakeOpenPulse2Q

def qasm_to_pulse_waveforms(qasm_str: str, backend) -> dict:
    try:
        # Parse the quantum circuit
        qc = QuantumCircuit.from_qasm_str(qasm_str)
        print(f"Parsed circuit:\n{qc.draw()}\n")
        
        # Check backend pulse support
        config = backend.configuration()
        if not hasattr(config, 'open_pulse') or not config.open_pulse:
            raise QiskitError(f"Backend {backend.name()} does not support pulse operations (open_pulse=False)")
        if not hasattr(backend, 'defaults'):
            raise QiskitError(f"Backend {backend.name()} lacks calibration data (no 'defaults' attribute)")
        print(f"Backend {backend.name()} supports pulse operations and contains calibration data\n")
        
        # Transpile the circuit (disable optimization, preserve original gates)
        transpiled_qc = transpile(
            qc, 
            backend, 
            optimization_level=0,  # No optimization to ensure pulse instructions are preserved
            basis_gates=['u3']     # Force use of u3 gates (must correspond to pulses)
        )
        print(f"Transpiled circuit:\n{transpiled_qc.draw()}\n")
        
        # Generate pulse schedule
        sched = schedule(transpiled_qc, backend)
        print(f"Pulse schedule contains {len(sched.instructions)} instructions, details as follows:")
        for i, (time, inst) in enumerate(sched.instructions):
            inst_type = type(inst).__name__
            channel_type = type(inst.channel).__name__ if hasattr(inst, 'channel') else 'No channel'
            pulse_type = type(inst.pulse).__name__ if hasattr(inst, 'pulse') else 'No pulse'
            print(f"  Instruction {i+1}: time={time}, type={inst_type}, channel type={channel_type}, pulse type={pulse_type}")
        
        # Extract pulse data
        pulse_arrays = {}
        for time, inst in sched.instructions:
            if isinstance(inst, Play) and isinstance(inst.channel, DriveChannel):
                if isinstance(inst.pulse, Waveform):
                    qubit = inst.channel.index
                    pulse_data = inst.pulse.samples
                    pulse_arrays[qubit] = pulse_arrays.get(qubit, []) + [pulse_data]
                    print(f"  Extracted pulse for qubit {qubit}, number of samples: {len(pulse_data)}")
        
        if not pulse_arrays:
            raise QiskitError("No pulse data extracted (no valid Play instructions)")
        
       # Merge pulse sequences
        for qubit in pulse_arrays:
            pulse_arrays[qubit] = np.concatenate(pulse_arrays[qubit])
        return [1,1,1,1,1]
        return pulse_arrays
    except Exception as e:
        raise QiskitError(f"Conversion failed: {str(e)}") from e

def plot_pulse_waveforms(waveforms: dict, backend):
    dt = backend.configuration().dt * 1e6  # Microsecond
    for qubit, wave_data in waveforms.items():
        time = np.arange(len(wave_data)) * dt
        i_component = wave_data.real
        q_component = wave_data.imag
        
        plt.figure(figsize=(12, 6))
        plt.suptitle(f'Pulse waveform for qubit {qubit} (X gate)', fontsize=14)
        
        plt.subplot(2, 1, 1)
        plt.plot(time, i_component, 'b-', label='I component (real part)')
        plt.xlabel('Time (microseconds)')
        plt.ylabel('Amplitude')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        
        plt.subplot(2, 1, 2)
        plt.plot(time, q_component, 'r-', label='Q component (imaginary part)')
        plt.xlabel('Time (microseconds)')
        plt.ylabel('Amplitude')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    # Ensure matplotlib is installed
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        import os
        os.system("pip install -i https://pypi.tuna.tsinghua.edu.cn/simple matplotlib")
        import matplotlib.pyplot as plt
    
    # Define QASM for X gate (guaranteed to generate pulses)
    qasm_str = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[1];
    u3(pi, 0, pi) q[0];  // X gate, guaranteed to correspond to a pulse
    """
    
    # Use backend specifically designed for pulses (FakeOpenPulse2Q)
    backend = FakeOpenPulse2Q()
    print(f"Using backend: {backend.name()}\n")
    
    try:
        waveforms = qasm_to_pulse_waveforms(qasm_str, backend)
        plot_pulse_waveforms(waveforms, backend)
    except QiskitError as e:
        print(f"\nRuntime error: {e}")