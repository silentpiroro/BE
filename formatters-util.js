// Helper function to format currency
export const formatCurrency = (amount) => {
  return '$' + amount.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
};

// Helper function to format percentage
export const formatPercent = (percent) => {
  return percent.toFixed(1) + '%';
};