import os
import torch
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from src.utils import load_checkpoint, load_config
from src.models.dgcnn import DGCNN
from src.data_loader import PointCloudDataset, get_train_test_dataloaders

def visualize_prediction(model, data, device, save_path=None):
    """Visualize ground truth classes and predicted classes"""
    model.eval()
    
    with torch.no_grad():
        data = data.to(device)
        outputs = model(data)
        predictions = torch.softmax(outputs, dim=1)  # Convert to probabilities
        pred_classes = predictions.argmax(dim=1).cpu().numpy()
    
    points = data.x.cpu().numpy()
    ground_truth = data.y.cpu().numpy()
    
    # Define colors and class names
    colors = ['blue', 'green', 'yellow', 'orange', 'red']
    class_names = ['No attention', 'Low', 'Medium-low', 'Medium-high', 'High']
    
    # Create figure with two subplots
    fig = plt.figure(figsize=(15, 7))
    
    # Ground truth classes (left)
    ax1 = fig.add_subplot(121, projection='3d')
    scatter1 = ax1.scatter(points[:, 0], points[:, 1], points[:, 2], 
                          c=[colors[int(c)] for c in ground_truth],
                          s=2)
    ax1.set_title(f"{data.metadata['form_type'][0].capitalize()} Model {data.metadata['form_number'][0]} - Ground Truth")
    
    # Add legend for ground truth
    legend_elements = [plt.Line2D([0], [0], marker='o', color='w',
                                markerfacecolor=c, label=class_names[i],
                                markersize=10)
                      for i, c in enumerate(colors)]
    ax1.legend(handles=legend_elements)
    
    # Predicted classes (right)
    ax2 = fig.add_subplot(122, projection='3d')
    scatter2 = ax2.scatter(points[:, 0], points[:, 1], points[:, 2], 
                          c=[colors[int(c)] for c in pred_classes],
                          s=2)
    ax2.set_title(f"{data.metadata['form_type'][0].capitalize()} Model {data.metadata['form_number'][0]} - Predicted")
    ax2.legend(handles=legend_elements)
    
    # Set consistent viewing angles and limits
    for ax in [ax1, ax2]:
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.view_init(elev=30, azim=45)
        
        max_range = np.array([
            points[:, 0].max() - points[:, 0].min(),
            points[:, 1].max() - points[:, 1].min(),
            points[:, 2].max() - points[:, 2].min()
        ]).max() / 2.0
        
        mid_x = (points[:, 0].max() + points[:, 0].min()) * 0.5
        mid_y = (points[:, 1].max() + points[:, 1].min()) * 0.5
        mid_z = (points[:, 2].max() + points[:, 2].min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
    
    # Add accuracy information
    accuracy = np.mean(pred_classes == ground_truth)
    plt.suptitle(f'Accuracy: {accuracy:.2%}', y=0.95)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    plt.show()
    
    # Print classification report
    print("\nClass Distribution:")
    for i in range(5):
        print(f"Class {i} ({class_names[i]}):")
        print(f"  Ground Truth: {np.sum(ground_truth == i)}")
        print(f"  Predicted: {np.sum(pred_classes == i)}")

def main():
    # Load configuration
    config = load_config("configs/config.yaml")
    
    # Device configuration
    device = torch.device("cpu")
    
    # Initialize model
    model = DGCNN(k=config['model']['k'], dropout=config['model']['dropout']).to(device)
    
    # Load the best model
    checkpoint_dir = config['training']['checkpoint_dir']
    timestamp_dirs = [d for d in os.listdir(checkpoint_dir) if os.path.isdir(os.path.join(checkpoint_dir, d))]
    if not timestamp_dirs:
        raise FileNotFoundError("No checkpoint directories found")
    latest_dir = max(timestamp_dirs)  # Get the most recent timestamp directory
    
    # Construct the path to best_model.pt
    checkpoint_path = os.path.join(checkpoint_dir, latest_dir, 'best_model.pt')
    print(f"Loading checkpoint from: {checkpoint_path}")  # Debug print
    
    checkpoint = torch.load(checkpoint_path)
    model.load_state_dict(checkpoint['model_state_dict'])
    
    # Load dataset
    dataset = PointCloudDataset(
        data_dir=config['data']['path'],
        demographic='novice'
    )
    
    # Get test loader with specific test models
    _, test_loader = get_train_test_dataloaders(
        dataset,
        test_models=[1, 15],
        batch_size=1
    )
    
    # Visualize predictions for test models
    for batch in test_loader:
        form_type = batch.metadata['form_type'][0]
        form_number = batch.metadata['form_number'][0]
        
        visualize_prediction(
            model=model,
            data=batch,
            device=device,
            save_path=f"visualization_{form_type}_model_{form_number}.png"
        )

if __name__ == "__main__":
    main() 