"""
Certificate generation command for the CLI tool.
"""

import argparse
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from terrarium_cli.commands.base import BaseCommand
from terrarium_cli.utils.shell import run_command, check_command_exists, ShellError
from terrarium_cli.utils.colors import Colors

logger = logging.getLogger(__name__)


class CertCommand(BaseCommand):
    """Command to generate TLS certificates for the Edge Terrarium project."""
    
    def __init__(self, args):
        super().__init__(args)
        self.project_root = Path(__file__).parent.parent.parent
        self.certs_dir = self.project_root / "certs"
        
        # Certificate configuration
        self.cert_name = "edge-terrarium"
        self.cert_file = self.certs_dir / f"{self.cert_name}.crt"
        self.key_file = self.certs_dir / f"{self.cert_name}.key"
        self.days_valid = 365
        
        # Subject information for the certificate
        self.country = "US"
        self.state = "California"
        self.city = "San Francisco"
        self.organization = "Edge Terrarium"
        self.organizational_unit = "Development"
        self.common_name = "edge-terrarium.local"
        self.email = "admin@edge-terrarium.local"
    
    @staticmethod
    def add_arguments(parser):
        """Add command-specific arguments to the parser."""
        parser.add_argument(
            "--force", "-f",
            action="store_true",
            help="Force regeneration of certificates even if they exist"
        )
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Number of days the certificate should be valid (default: 365)"
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            help="Directory to output certificates (default: ./certs)"
        )
    
    def run(self) -> int:
        """Run the certificate generation command."""
        try:
            # Update days_valid if specified
            if hasattr(self.args, 'days') and self.args.days:
                self.days_valid = self.args.days
            
            # Update output directory if specified
            if hasattr(self.args, 'output_dir') and self.args.output_dir:
                self.certs_dir = Path(self.args.output_dir)
                self.cert_file = self.certs_dir / f"{self.cert_name}.crt"
                self.key_file = self.certs_dir / f"{self.cert_name}.key"
            
            print(f"{Colors.BLUE}============================================================================={Colors.RESET}")
            print(f"{Colors.BLUE}DYNAMIC TLS CERTIFICATE GENERATION{Colors.RESET}")
            print(f"{Colors.BLUE}============================================================================={Colors.RESET}")
            print(f"Project Root: {self.project_root}")
            print(f"Certificates Directory: {self.certs_dir}")
            print(f"Certificate Name: {self.cert_name}")
            print(f"Days Valid: {self.days_valid}")
            print(f"{Colors.BLUE}============================================================================={Colors.RESET}")
            print()
            
            # Check prerequisites
            if not self._check_prerequisites():
                return 1
            
            # Check for existing certificates
            if not self.args.force and self._check_existing_certificates():
                self._display_certificate_info()
                return 0
            
            # Generate new certificates
            if not self._generate_tls_certificate():
                return 1
            
            # Verify certificates
            if not self._verify_certificates():
                return 1
            
            # Set file permissions
            self._set_file_permissions()
            
            # Display information
            self._display_certificate_info()
            
            print(f"{Colors.GREEN}TLS certificate generation completed successfully!{Colors.RESET}")
            return 0
            
        except Exception as e:
            logger.error(f"Certificate generation failed: {e}")
            print(f"{Colors.RED}Certificate generation failed: {e}{Colors.RESET}")
            return 1
    
    def _check_prerequisites(self) -> bool:
        """Check if required prerequisites are available."""
        print(f"{Colors.BLUE}[INFO]{Colors.RESET} Checking prerequisites...")
        
        # Check if openssl is installed
        if not check_command_exists("openssl"):
            print(f"{Colors.RED}[ERROR]{Colors.RESET} openssl is required but not installed")
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} Please install openssl:")
            print(f"{Colors.BLUE}[INFO]{Colors.RESET}   - macOS: brew install openssl")
            print(f"{Colors.BLUE}[INFO]{Colors.RESET}   - Ubuntu/Debian: sudo apt-get install openssl")
            print(f"{Colors.BLUE}[INFO]{Colors.RESET}   - CentOS/RHEL: sudo yum install openssl")
            return False
        
        # Check if certs directory exists
        if not self.certs_dir.exists():
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} Creating certs directory: {self.certs_dir}")
            self.certs_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} Prerequisites check passed")
        return True
    
    def _check_existing_certificates(self) -> bool:
        """Check if certificates already exist and are valid."""
        if self.cert_file.exists() and self.key_file.exists():
            # Check certificate expiration
            try:
                result = run_command([
                    "openssl", "x509", "-in", str(self.cert_file), 
                    "-noout", "-enddate"
                ], capture_output=True)
                if result.returncode == 0:
                    expiry_date = result.stdout.strip().split("=", 1)[1]
                    print(f"{Colors.BLUE}[INFO]{Colors.RESET} Using existing certificates (expires: {expiry_date})")
                else:
                    print(f"{Colors.BLUE}[INFO]{Colors.RESET} Using existing certificates")
            except Exception:
                print(f"{Colors.BLUE}[INFO]{Colors.RESET} Using existing certificates")
            
            return True  # Use existing certificates
        
        return False  # Generate new certificates
    
    def _generate_tls_certificate(self) -> bool:
        """Generate TLS certificate and private key."""
        print(f"{Colors.BLUE}[INFO]{Colors.RESET} Generating TLS certificate and private key...")
        
        try:
            # Create a temporary configuration file for openssl
            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as config_file:
                config_content = f"""[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C={self.country}
ST={self.state}
L={self.city}
O={self.organization}
OU={self.organizational_unit}
CN={self.common_name}
emailAddress={self.email}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = edge-terrarium.local
DNS.2 = localhost
DNS.3 = *.edge-terrarium.local
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
"""
                config_file.write(config_content)
                config_file_path = config_file.name
            
            # Generate private key
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} Generating private key...")
            result = run_command([
                "openssl", "genrsa", "-out", str(self.key_file), "2048"
            ])
            if result.returncode != 0:
                print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to generate private key")
                return False
            
            # Generate certificate signing request
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} Generating certificate signing request...")
            with tempfile.NamedTemporaryFile(suffix='.csr', delete=False) as csr_file:
                csr_file_path = csr_file.name
            
            result = run_command([
                "openssl", "req", "-new", "-key", str(self.key_file), 
                "-out", csr_file_path, "-config", config_file_path
            ])
            if result.returncode != 0:
                print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to generate certificate signing request")
                return False
            
            # Generate self-signed certificate
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} Generating self-signed certificate...")
            result = run_command([
                "openssl", "x509", "-req", "-in", csr_file_path, 
                "-signkey", str(self.key_file), "-out", str(self.cert_file), 
                "-days", str(self.days_valid), "-extensions", "v3_req", 
                "-extfile", config_file_path
            ])
            if result.returncode != 0:
                print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to generate self-signed certificate")
                return False
            
            # Clean up temporary files
            Path(config_file_path).unlink(missing_ok=True)
            Path(csr_file_path).unlink(missing_ok=True)
            
            print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} TLS certificate and private key generated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Certificate generation failed: {e}")
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Certificate generation failed: {e}")
            return False
    
    def _verify_certificates(self) -> bool:
        """Verify generated certificates."""
        print(f"{Colors.BLUE}[INFO]{Colors.RESET} Verifying generated certificates...")
        
        # Check if files exist
        if not self.cert_file.exists() or not self.key_file.exists():
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Certificate files were not created")
            return False
        
        try:
            # Verify certificate
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} Certificate details:")
            result = run_command([
                "openssl", "x509", "-in", str(self.cert_file), 
                "-text", "-noout"
            ], capture_output=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if any(keyword in line for keyword in ["Subject:", "Issuer:", "Not Before:", "Not After:", "DNS:", "IP Address:"]):
                        print(f"  {line.strip()}")
            
            # Verify private key
            print(f"{Colors.BLUE}[INFO]{Colors.RESET} Private key details:")
            result = run_command([
                "openssl", "rsa", "-in", str(self.key_file), "-check", "-noout"
            ], capture_output=True)
            if result.returncode == 0:
                print(f"  {result.stdout.strip()}")
            
            # Verify certificate and key match
            cert_result = run_command([
                "openssl", "x509", "-noout", "-modulus", "-in", str(self.cert_file)
            ], capture_output=True)
            key_result = run_command([
                "openssl", "rsa", "-noout", "-modulus", "-in", str(self.key_file)
            ], capture_output=True)
            
            if cert_result.returncode == 0 and key_result.returncode == 0:
                cert_md5 = subprocess.run(
                    ["openssl", "md5"], 
                    input=cert_result.stdout, 
                    text=True,
                    capture_output=True
                ).stdout.strip()
                key_md5 = subprocess.run(
                    ["openssl", "md5"], 
                    input=key_result.stdout, 
                    text=True,
                    capture_output=True
                ).stdout.strip()
                
                if cert_md5 == key_md5:
                    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} Certificate and private key match")
                else:
                    print(f"{Colors.RED}[ERROR]{Colors.RESET} Certificate and private key do not match")
                    return False
            
            print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} Certificate verification completed")
            return True
            
        except Exception as e:
            logger.error(f"Certificate verification failed: {e}")
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Certificate verification failed: {e}")
            return False
    
    def _set_file_permissions(self) -> None:
        """Set proper file permissions on generated certificates."""
        print(f"{Colors.BLUE}[INFO]{Colors.RESET} Setting file permissions...")
        
        try:
            # Set restrictive permissions on private key
            self.key_file.chmod(0o600)
            
            # Set readable permissions on certificate
            self.cert_file.chmod(0o644)
            
            print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} File permissions set")
        except Exception as e:
            logger.warning(f"Failed to set file permissions: {e}")
            print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} Failed to set file permissions: {e}")
    
    def _display_certificate_info(self) -> None:
        """Display certificate information."""
        print()
        print(f"{Colors.BLUE}============================================================================={Colors.RESET}")
        print(f"{Colors.BLUE}TLS CERTIFICATE GENERATION COMPLETED{Colors.RESET}")
        print(f"{Colors.BLUE}============================================================================={Colors.RESET}")
        print(f"Certificate: {self.cert_file}")
        print(f"Private Key: {self.key_file}")
        print(f"Valid for: {self.days_valid} days")
        print()
        print("Certificate Details:")
        print(f"  Common Name: {self.common_name}")
        print(f"  Organization: {self.organization}")
        print("  Subject Alternative Names:")
        print("    - edge-terrarium.local")
        print("    - localhost")
        print("    - *.edge-terrarium.local")
        print("    - 127.0.0.1")
        print("    - 0.0.0.0")
        print()
        print("Next Steps:")
        print("  1. The certificates will be automatically loaded into Vault")
        print("  2. NGINX Gateway will use these certificates for HTTPS")
        print("  3. You can access the application at https://localhost:8443")
        print("  4. You may need to accept the self-signed certificate in your browser")
        print(f"{Colors.BLUE}============================================================================={Colors.RESET}")
