'use strict';

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('id_image');
  const preview = document.querySelector('[data-image-preview]');
  if (!input || !preview) return;

  const image = preview.querySelector('img');
  const caption = preview.querySelector('figcaption');
  const currentImage = image.dataset.currentImage;
  let selectedImageUrl;

  function releaseSelectedImage() {
    if (selectedImageUrl) URL.revokeObjectURL(selectedImageUrl);
    selectedImageUrl = undefined;
  }

  image.addEventListener('error', () => {
    image.hidden = true;
    caption.textContent = 'Rasmni ko‘rsatib bo‘lmadi. Boshqa rasm tanlang.';
  });

  function showPreview() {
    releaseSelectedImage();
    const file = input.files[0];
    if (file) {
      selectedImageUrl = URL.createObjectURL(file);
      image.src = selectedImageUrl;
      image.hidden = false;
      caption.textContent = 'Tanlangan rasm. O‘zgarishlarni saqlagandan keyin saytda ko‘rinadi.';
    } else if (currentImage) {
      image.src = currentImage;
      image.hidden = false;
      caption.textContent = 'Mavjud rasm';
    } else {
      image.removeAttribute('src');
      image.hidden = true;
      caption.textContent = 'Rasm tanlanganda shu yerda ko‘rinadi.';
    }
  }

  input.addEventListener('change', showPreview);
  window.addEventListener('pagehide', releaseSelectedImage);
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) showPreview();
  });
});
