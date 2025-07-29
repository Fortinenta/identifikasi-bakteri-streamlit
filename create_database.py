import pandas as pd

def create_database():
    columns = [
        "Nama_Bakteri", "Gram stain", "Ziehl-Neelsen (AFB)", "Endospore stain", "Capsule stain", 
        "Flagella stain", "Cell shape", "Motility", "Spore formation", "Colony morphology", 
        "Colony color", "Flagella arrangement", "Catalase", "Oxidase", "Indole", "Methyl Red", 
        "Voges-Proskauer", "Citrate utilization", "Urease", "H2S production", "Nitrate reduction", 
        "Gelatin hydrolysis", "Starch hydrolysis", "Casein hydrolysis", "DNAse test", 
        "TSI (Triple Sugar Iron)", "Lysine Decarboxylase", "Ornithine Decarboxylase", 
        "Arginine Dihydrolase", "Glucose", "Lactose", "Sucrose", "Maltose", "Mannitol", 
        "Sorbitol", "Xylose", "Rhamnose", "Arabinose", "Inositol", "Trehalose", "Raffinose", 
        "Adonitol", "Dulcitol", "Salicin", "Cellobiose", "Beta-galactosidase", 
        "Phenylalanine deaminase", "Lipase", "Alkaline phosphatase", "Arginine hydrolysis", 
        "Temperature range", "pH tolerance", "NaCl tolerance", "Oxygen requirement", 
        "PCR 16S rRNA", "Whole Genome Sequencing", "MALDI-TOF MS", 
        "Antibiotic susceptibility (disc diffusion)", "MIC (Minimum Inhibitory Concentration)",
        "Deskripsi", "Habitat", "Patogenisitas"
    ]
    
    # Example data for a few bacteria
    data = {
        "Nama_Bakteri": ["Escherichia coli", "Staphylococcus aureus"],
        "Gram stain": ["Negative", "Positive"],
        # Add more data for other columns as needed
    }

    df = pd.DataFrame(data, columns=columns)
    df.to_excel("database_bakteri.xlsx", index=False)
    print("Database file 'database_bakteri.xlsx' created successfully.")

if __name__ == "__main__":
    create_database()
