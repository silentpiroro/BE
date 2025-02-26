// Default data for three business models
export const defaultB2B = {
  minOrder: 180,
  materials: 3.2,
  labor: 1.1,
  overhead: 0.8,
  packaging: 0.3,
  shipping: 1.8,
  markup: 30,
};

export const defaultB2B2C = {
  packages: [
    { name: 'Small', quantity: 20, printingCost: 1.2, embroideryAdditional: 0.5, wovenLabelAdditional: 0.3, baseSockCost: 2.5, markup: 40 },
    { name: 'Medium', quantity: 60, printingCost: 1.0, embroideryAdditional: 0.4, wovenLabelAdditional: 0.25, baseSockCost: 2.3, markup: 35 },
    { name: 'Large', quantity: 120, printingCost: 0.8, embroideryAdditional: 0.3, wovenLabelAdditional: 0.2, baseSockCost: 2.1, markup: 30 }
  ],
  selectedDecorationMethod: 'Printing'
};

export const defaultB2C = {
  packages: [
    { name: 'Diabetic 3-Pack', pairs: 3, costPerPair: 2.8, packaging: 0.7, markup: 65 },
    { name: 'Diabetic 6-Pack', pairs: 6, costPerPair: 2.7, packaging: 0.9, markup: 60 },
    { name: 'Compression 3-Pack', pairs: 3, costPerPair: 3.9, packaging: 0.7, markup: 70 },
    { name: 'Compression 6-Pack', pairs: 6, costPerPair: 3.7, packaging: 0.9, markup: 65 }
  ],
  monthlyVolume: [
    { name: 'Diabetic 3-Pack', units: 150 },
    { name: 'Diabetic 6-Pack', units: 120 },
    { name: 'Compression 3-Pack', units: 180 },
    { name: 'Compression 6-Pack', units: 130 }
  ]
};

// Sample monthly fixed costs
export const defaultFixedCosts = {
  rent: 2500,
  utilities: 800,
  salaries: 12000,
  marketing: 3500,
  software: 500,
  otherFixed: 1000
};