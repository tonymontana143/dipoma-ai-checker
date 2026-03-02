# Иконки для ToxicShield Extension

## 📦 Требуемые файлы

Расширению нужны 3 иконки:
- `icon16.png` - 16x16 пикселей (для панели расширений)
- `icon48.png` - 48x48 пикселей (для страницы управления расширениями)
- `icon128.png` - 128x128 пикселей (для Chrome Web Store)

## 🎨 Дизайн

**Рекомендуемый стиль:**
- Фон: градиент от `#667eea` (синий) до `#764ba2` (фиолетовый)
- Символ: белый щит 🛡 или буква "T"
- Стиль: современный, минималистичный

## 🚀 Быстрое создание

### Вариант 1: ImageMagick (простой)
```bash
# Создаем иконку со щитом
convert -size 128x128 xc:'#667eea' \
  -font Arial -pointsize 80 -fill white \
  -gravity center -annotate +0+0 "🛡" \
  icon128.png

# Создаем меньшие размеры
convert icon128.png -resize 48x48 icon48.png
convert icon128.png -resize 16x16 icon16.png
```

### Вариант 2: Python + Pillow
```bash
pip install pillow

python3 << 'EOF'
from PIL import Image, ImageDraw

for size in [128, 48, 16]:
    img = Image.new('RGB', (size, size), color='#667eea')
    draw = ImageDraw.Draw(img)
    # Простой круг в центре
    padding = size // 4
    draw.ellipse([padding, padding, size-padding, size-padding], 
                 fill='white', outline='#764ba2', width=max(1, size//32))
    img.save(f'icon{size}.png')
    print(f'Created icon{size}.png')
EOF
```

### Вариант 3: Онлайн генератор
1. Откройте https://favicon.io/favicon-generator/
2. Настройки:
   - Text: T
   - Background: Gradient (#667eea → #764ba2)
   - Font Color: #FFFFFF
   - Font Size: 80
3. Download
4. Переименуйте файлы в icon16.png, icon48.png, icon128.png

### Вариант 4: Ручное создание
Создайте в любом графическом редакторе (Figma, Photoshop, GIMP):
1. Создайте 128x128px файл
2. Залейте градиентом (#667eea → #764ba2)
3. Добавьте белый символ щита или "T"
4. Экспортируйте в PNG
5. Создайте копии 48x48 и 16x16

## ✅ Проверка

После создания проверьте:
```bash
ls -lh
# Должно быть 3 файла: icon16.png, icon48.png, icon128.png

file icon*.png
# Все должны быть PNG image data
```

## 🔧 Если иконок нет

Расширение не запустится без иконок. Временное решение:

**Создайте простые цветные квадраты:**
```bash
convert -size 128x128 xc:'#667eea' icon128.png
convert -size 48x48 xc:'#667eea' icon48.png
convert -size 16x16 xc:'#667eea' icon16.png
```

Или используйте любые PNG изображения правильного размера.
