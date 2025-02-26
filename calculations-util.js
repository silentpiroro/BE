// B2B calculations
export const calculateB2B = (b2bData, b2bVolume) => {
  const { minOrder, materials, labor, overhead, packaging, shipping, markup } = b2bData;
  const costPerUnit = materials + labor + overhead + packaging + shipping;
  const pricePerUnit = costPerUnit * (1 + markup / 100);
  const totalOrderCost = costPerUnit * minOrder;
  const totalOrderPrice = pricePerUnit * minOrder;
  const profit = totalOrderPrice - totalOrderCost;
  const profitMargin = (profit / totalOrderPrice) * 100;
  
  const monthlySales = totalOrderPrice * b2bVolume;
  const monthlyCost = totalOrderCost * b2bVolume;
  const monthlyProfit = profit * b2bVolume;
  
  return {
    costPerUnit,
    pricePerUnit,
    totalOrderCost,
    totalOrderPrice,
    profit,
    profitMargin,
    monthlySales,
    monthlyCost,
    monthlyProfit
  };
};

// B2B2C calculations
export const calculateB2B2C = (b2b2cData) => {
  const { packages, selectedDecorationMethod } = b2b2cData;
  
  const calculatedPackages = packages.map(pkg => {
    let decorationCost = pkg.printingCost; // Default to printing
    if (selectedDecorationMethod === 'Embroidery') {
      decorationCost = pkg.printingCost + pkg.embroideryAdditional;
    } else if (selectedDecorationMethod === 'Woven Label') {
      decorationCost = pkg.printingCost + pkg.wovenLabelAdditional;
    }
    
    const costPerUnit = pkg.baseSockCost + decorationCost;
    const costPerPackage = costPerUnit * pkg.quantity;
    const pricePerPackage = costPerPackage * (1 + pkg.markup / 100);
    const profit = pricePerPackage - costPerPackage;
    const profitMargin = (profit / pricePerPackage) * 100;
    
    // Assume some monthly sales volume
    const monthlySales = pkg.quantity === 20 ? 25 : (pkg.quantity === 60 ? 18 : 12);
    const monthlySalesValue = pricePerPackage * monthlySales;
    const monthlyCost = costPerPackage * monthlySales;
    const monthlyProfit = profit * monthlySales;
    
    return {
      ...pkg,
      decorationCost,
      costPerUnit,
      costPerPackage,
      pricePerPackage,
      profit,
      profitMargin,
      monthlySales,
      monthlySalesValue,
      monthlyCost,
      monthlyProfit
    };
  });
  
  const totalMonthlySales = calculatedPackages.reduce((sum, pkg) => sum + pkg.monthlySalesValue, 0);
  const totalMonthlyCost = calculatedPackages.reduce((sum, pkg) => sum + pkg.monthlyCost, 0);
  const totalMonthlyProfit = calculatedPackages.reduce((sum, pkg) => sum + pkg.monthlyProfit, 0);
  
  return {
    packages: calculatedPackages,
    totalMonthlySales,
    totalMonthlyCost,
    totalMonthlyProfit
  };
};

// B2C calculations
export const calculateB2C = (b2cData) => {
  const { packages, monthlyVolume } = b2cData;
  
  const calculatedPackages = packages.map(pkg => {
    const totalCostPerPackage = (pkg.costPerPair * pkg.pairs) + pkg.packaging;
    const pricePerPackage = totalCostPerPackage * (1 + pkg.markup / 100);
    const profit = pricePerPackage - totalCostPerPackage;
    const profitMargin = (profit / pricePerPackage) * 100;
    
    // Find corresponding monthly volume
    const volume = monthlyVolume.find(v => v.name === pkg.name)?.units || 0;
    const monthlySales = pricePerPackage * volume;
    const monthlyCost = totalCostPerPackage * volume;
    const monthlyProfit = profit * volume;
    
    return {
      ...pkg,
      totalCostPerPackage,
      pricePerPackage,
      profit,
      profitMargin,
      volume,
      monthlySales,
      monthlyCost,
      monthlyProfit
    };
  });
  
  const totalMonthlySales = calculatedPackages.reduce((sum, pkg) => sum + pkg.monthlySales, 0);
  const totalMonthlyCost = calculatedPackages.reduce((sum, pkg) => sum + pkg.monthlyCost, 0);
  const totalMonthlyProfit = calculatedPackages.reduce((sum, pkg) => sum + pkg.monthlyProfit, 0);
  
  return {
    packages: calculatedPackages,
    totalMonthlySales,
    totalMonthlyCost,
    totalMonthlyProfit
  };
};

// Income statement calculation
export const generateIncomeStatement = (b2bResults, b2b2cResults, b2cResults, fixedCostsData) => {
  const totalRevenue = b2bResults.monthlySales + b2b2cResults.totalMonthlySales + b2cResults.totalMonthlySales;
  const totalCogs = b2bResults.monthlyCost + b2b2cResults.totalMonthlyCost + b2cResults.totalMonthlyCost;
  const grossProfit = totalRevenue - totalCogs;
  const grossMargin = (grossProfit / totalRevenue) * 100;
  
  const totalFixedCosts = Object.values(fixedCostsData).reduce((sum, cost) => sum + cost, 0);
  const operatingProfit = grossProfit - totalFixedCosts;
  const netMargin = (operatingProfit / totalRevenue) * 100;
  
  // Calculate revenue distribution for pie chart
  const revenueDistribution = [
    { name: 'B2B OEM', value: b2bResults.monthlySales },
    { name: 'B2B2C Custom', value: b2b2cResults.totalMonthlySales },
    { name: 'B2C Retail', value: b2cResults.totalMonthlySales }
  ];
  
  // Calculate profit distribution for pie chart
  const profitDistribution = [
    { name: 'B2B OEM', value: b2bResults.monthlyProfit },
    { name: 'B2B2C Custom', value: b2b2cResults.totalMonthlyProfit },
    { name: 'B2C Retail', value: b2cResults.totalMonthlyProfit }
  ];
  
  return {
    totalRevenue,
    totalCogs,
    grossProfit,
    grossMargin,
    totalFixedCosts,
    operatingProfit,
    netMargin,
    revenueDistribution,
    profitDistribution,
    b2bRevenue: b2bResults.monthlySales,
    b2b2cRevenue: b2b2cResults.totalMonthlySales,
    b2cRevenue: b2cResults.totalMonthlySales
  };
};