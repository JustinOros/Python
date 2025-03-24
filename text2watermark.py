1 #!/usr/bin/python3
  2 # Description: Convert text to watermark (PNG)
  3 # Usage: python3 text2watermark.py <text>
  4 # Author: Justin Oros
  5 # Source: https://github.com/JustinOros
  6 
  7 import sys
  8 from PIL import Image, ImageDraw, ImageFont
  9 
 10 def create_watermark(text, output_path="watermark.png", size=(150, 150)):
 11     # Create a transparent image
 12     img = Image.new("RGBA", size, (255, 255, 255, 0))
 13     draw = ImageDraw.Draw(img)
 14 
 15     # Load font
 16     try:
 17         font = ImageFont.truetype("arial.ttf", 20)
 18     except IOError:
 19         font = ImageFont.load_default()
 20 
 21     # Set text size and position
 22     text_size = draw.textbbox((0, 0), text, font=font)
 23     text_width = text_size[2] - text_size[0]
 24     text_height = text_size[3] - text_size[1]
 25     position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
 26 
 27     # Draw text on transparent background
 28     draw.text(position, text, fill=(0, 0, 0, 255), font=font)
 29 
 30     # Save the image
 31     img.save(output_path, "PNG")
 32     print(f"Watermark saved as {output_path}")
 33 
 34 if __name__ == "__main__":
 35     if len(sys.argv) != 2:
 36         print("Usage: python3 text2watermark.py <WatermarkText>")
 37         sys.exit(1)
 38 
 39     text_input = sys.argv[1]
 40     create_watermark(text_input)
