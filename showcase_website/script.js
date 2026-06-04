// Simple smooth scroll and interactions
document.addEventListener('DOMContentLoaded', () => {
  console.log('%cMultiDisk FileBalancer Landing Page loaded 🚀', 'color: #34d399; font-size: 14px;');
  
  // Add subtle animation to cards
  const cards = document.querySelectorAll('.card');
  cards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(30px)';
    
    setTimeout(() => {
      card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
      card.style.transitionDelay = `${index * 100}ms`;
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 300);
  });
});
