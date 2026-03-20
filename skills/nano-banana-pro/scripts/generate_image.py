#!/usr/bin/env python3
"""
Generate images using Google's Nano Banana Pro (Gemini 3 Pro Image) API.

Usage:
    python3 generate_image.py --prompt "your image description" --filename "output.png" [--resolution 1K|2K|4K] [--api-key KEY]
"""

import argparse
import os
import sys
import json
import base64
import socket
import socks  # PySocks for SOCKS proxy support
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error


def get_api_key(provided_key: Optional[str]) -> Optional[str]:
    """Get API key from argument first, then environment."""
    if provided_key:
        return provided_key
    return os.environ.get("GEMINI_API_KEY")


def setup_proxy():
    """Setup SOCKS5 proxy if available."""
    # Check for proxy environment variables
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    
    proxy_url = https_proxy or http_proxy
    
    if proxy_url and ('socks' in proxy_url.lower() or ':1080' in proxy_url):
        try:
            if '://' in proxy_url:
                _, addr = proxy_url.split('://', 1)
            else:
                addr = proxy_url
            
            if '@' in addr:
                auth, addr = addr.split('@', 1)
            
            host, port = addr.split(':')
            port = int(port)
            
            print(f"Using SOCKS5 proxy: {host}:{port}")
            
            socks.set_default_proxy(socks.SOCKS5, host, port)
            socket.socket = socks.socksocket
            return True
        except Exception as e:
            print(f"Warning: Failed to setup proxy: {e}", file=sys.stderr)
            return False
    
    # Try default localhost:1080
    try:
        import socket as sock_module
        test_sock = sock_module.socket(sock_module.AF_INET, sock_module.SOCK_STREAM)
        test_sock.settimeout(2)
        test_sock.connect(('127.0.0.1', 1080))
        test_sock.close()
        
        print("Using SOCKS5 proxy: 127.0.0.1:1080")
        socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 1080)
        socket.socket = socks.socksocket
        return True
    except:
        pass
    
    return False


def call_gemini_api(api_key: str, prompt: str, resolution: str = "1K", input_image_path: Optional[str] = None):
    """Call Gemini API to generate image."""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}"
    
    # Build request body
    if input_image_path and os.path.exists(input_image_path):
        with open(input_image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        ext = Path(input_image_path).suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_types.get(ext, 'image/png')
        
        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": image_data
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["Text", "Image"]
            }
        }
    else:
        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["Text", "Image"]
            }
        }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"API error {e.code}: {error_body}")
    except Exception as e:
        raise Exception(f"Request failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Nano Banana Pro (Gemini 3 Pro Image)"
    )
    parser.add_argument("--prompt", "-p", required=True, help="Image description/prompt")
    parser.add_argument("--filename", "-f", required=True, help="Output filename")
    parser.add_argument("--input-image", "-i", help="Optional input image path")
    parser.add_argument("--resolution", "-r", choices=["1K", "2K", "4K"], default="1K")
    parser.add_argument("--api-key", "-k", help="Gemini API key")
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy")

    args = parser.parse_args()

    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        sys.exit(1)

    if not args.no_proxy:
        proxy_enabled = setup_proxy()
        if not proxy_enabled:
            print("Warning: No proxy configured.", file=sys.stderr)

    output_path = Path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_resolution = args.resolution
    if args.input_image:
        if not os.path.exists(args.input_image):
            print(f"Error: Input image not found: {args.input_image}", file=sys.stderr)
            sys.exit(1)
        
        from PIL import Image as PILImage
        try:
            input_image = PILImage.open(args.input_image)
            print(f"Loaded input image: {args.input_image}")

            if args.resolution == "1K":
                width, height = input_image.size
                max_dim = max(width, height)
                if max_dim >= 3000:
                    output_resolution = "4K"
                elif max_dim >= 1500:
                    output_resolution = "2K"
                else:
                    output_resolution = "1K"
                print(f"Auto-detected resolution: {output_resolution}")
        except Exception as e:
            print(f"Error loading input image: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        if args.input_image:
            print(f"Editing image with resolution {output_resolution}...")
        else:
            print(f"Generating image with resolution {output_resolution}...")
        
        result = call_gemini_api(api_key, args.prompt, output_resolution, args.input_image)
        
        image_saved = False
        text_response = []
        
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                for part in candidate['content']['parts']:
                    if 'text' in part:
                        text_response.append(part['text'])
                    elif 'inlineData' in part:
                        image_data = part['inlineData']['data']
                        image_bytes = base64.b64decode(image_data)
                        
                        from PIL import Image as PILImage
                        from io import BytesIO
                        
                        image = PILImage.open(BytesIO(image_bytes))
                        
                        if image.mode == 'RGBA':
                            rgb_image = PILImage.new('RGB', image.size, (255, 255, 255))
                            rgb_image.paste(image, mask=image.split()[3])
                            rgb_image.save(str(output_path), 'PNG')
                        elif image.mode == 'RGB':
                            image.save(str(output_path), 'PNG')
                        else:
                            image.convert('RGB').save(str(output_path), 'PNG')
                        
                        image_saved = True
        
        if text_response:
            print(f"Model response: {' '.join(text_response)}")
        
        if image_saved:
            full_path = output_path.resolve()
            print(f"\nImage saved: {full_path}")
        else:
            print("Error: No image was generated.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()