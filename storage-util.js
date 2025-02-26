// Save configuration to local storage
export const saveConfiguration = (config) => {
  try {
    localStorage.setItem('sockBusinessConfig', JSON.stringify(config));
    return true;
  } catch (error) {
    console.error('Error saving configuration:', error);
    return false;
  }
};

// Load configuration from local storage
export const loadConfiguration = () => {
  try {
    const savedConfig = localStorage.getItem('sockBusinessConfig');
    if (savedConfig) {
      return JSON.parse(savedConfig);
    }
    return null;
  } catch (error) {
    console.error('Error loading configuration:', error);
    return null;
  }
};

// Export data to CSV
export const exportToCsv = (incomeStatement, fixedCostsData) => {
  // Create CSV content
  let csvContent = "data:text/csv;charset=utf-8,";
  
  // Income Statement
  csvContent += "Monthly Income Statement\n";
  csvContent += "Revenue,Amount\n";
  csvContent += `B2B OEM Revenue,${incomeStatement.b2bRevenue}\n`;
  csvContent += `B2B2C Custom Revenue,${incomeStatement.b2b2cRevenue}\n`;
  csvContent += `B2C Retail Revenue,${incomeStatement.b2cRevenue}\n`;
  csvContent += `Total Revenue,${incomeStatement.totalRevenue}\n\n`;
  
  csvContent += "COGS,Amount\n";
  csvContent += `Total COGS,${incomeStatement.totalCogs}\n\n`;
  
  csvContent += `Gross Profit,${incomeStatement.grossProfit}\n`;
  csvContent += `Gross Margin,${incomeStatement.grossMargin}%\n\n`;
  
  csvContent += "Fixed Expenses,Amount\n";
  Object.entries(fixedCostsData).forEach(([key, value]) => {
    csvContent += `${key.charAt(0).toUpperCase() + key.slice(1)},${value}\n`;
  });
  csvContent += `Total Fixed Expenses,${incomeStatement.totalFixedCosts}\n\n`;
  
  csvContent += `Operating Profit,${incomeStatement.operatingProfit}\n`;
  csvContent += `Net Margin,${incomeStatement.netMargin}%\n\n`;
  
  // Create download link
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "sock_business_income_statement.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};